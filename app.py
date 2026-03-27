from flask import Flask, request, jsonify, Response, send_file, stream_with_context
from flask_cors import CORS
from openai import OpenAI, RateLimitError, APITimeoutError, APIError
from dotenv import load_dotenv
from mcp_server import fs_list_files, fs_create_file, fs_read_file, fs_update_file, fs_delete_file
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import db
import converter
import json
import logging
import os
import re
import threading
import queue
from datetime import datetime

# New core imports
from core.shared import (
    client, MODEL, OPENROUTER_API_KEY, _ALLOWED_ROOTS,
    _DEFAULT_WORKSPACE, _workspace_lock, _ws_change_queues, _ws_change_lock,
    TEMP_DIR, _notify_workspace_changed, get_workspace, set_workspace
)
from core.utils import load_prompt, execute_tool, format_sse
from core.orchestrator import Orchestrator
from core.agent_factory import AgentFactory

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_MAX_PENDING_DOC_BYTES = int(os.getenv('MAX_PENDING_DOC_BYTES', str(200 * 1024)))  # 200KB default

# Suppress WeasyPrint's extremely verbose font subsetting logs
logging.getLogger('fontTools').setLevel(logging.ERROR)
logging.getLogger('weasyprint').setLevel(logging.WARNING)


def _extract_json(raw: str) -> str:
    """Extract JSON from LLM output that may have markdown fences or surrounding prose."""
    cleaned = re.sub(r'```[^\n]*\n?', '', raw)
    cleaned = cleaned.replace('```', '').strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in LLM output: {raw[:200]!r}")
    return cleaned[start:end + 1]


def _normalize_workspace_path(path: str) -> str:
    """Normalize a workspace path relative to the current process."""
    return os.path.abspath(path or _DEFAULT_WORKSPACE)


def _is_allowed_workspace_path(path: str) -> bool:
    """Allow runtime workspace changes only under configured allowed roots."""
    try:
        real = os.path.realpath(path)
        return any(
            os.path.commonpath([root, real]) == root
            for root in _ALLOWED_ROOTS
        )
    except ValueError:
        return False

# ─── MCP Tool Definitions (OpenAI function calling format) ────────────────────

MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "สร้างไฟล์ใหม่ใน workspace พร้อมเนื้อหา ใช้เพื่อบันทึกเอกสารที่สร้างขึ้น",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "ชื่อไฟล์พร้อมนามสกุล เช่น contract_somchai.md หรือ invoice_001.md"
                    },
                    "content": {
                        "type": "string",
                        "description": "เนื้อหาทั้งหมดของไฟล์ในรูปแบบ Markdown"
                    }
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "อ่านเนื้อหาของไฟล์ที่มีอยู่ใน workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "ชื่อไฟล์ที่ต้องการอ่าน"
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_file",
            "description": "แก้ไขเนื้อหาของไฟล์ที่มีอยู่แล้วใน workspace (เขียนทับทั้งหมด)",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "ชื่อไฟล์ที่ต้องการแก้ไข"
                    },
                    "content": {
                        "type": "string",
                        "description": "เนื้อหาใหม่ทั้งหมด"
                    }
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "ลบไฟล์จาก workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "ชื่อไฟล์ที่ต้องการลบ"
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "แสดงรายการไฟล์ทั้งหมดที่มีอยู่ใน workspace",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "ค้นหาข้อมูลจากอินเทอร์เน็ต ใช้เมื่อผู้ใช้ถามเกี่ยวกับข้อมูลปัจจุบัน "
                "เช่น กฎหมายล่าสุด อัตราภาษี แนวโน้มตลาด ข่าวสาร หรือข้อมูลที่อาจเปลี่ยนแปลงบ่อย"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "คำค้นหาภาษาไทยหรือภาษาอังกฤษ"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "จำนวนผลลัพธ์สูงสุด ระบุ 3-5 เท่านั้น"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

READ_ONLY_TOOLS = [t for t in MCP_TOOLS if t['function']['name'] in ('list_files', 'read_file', 'web_search')]

_LOCAL_DELETE_TOOL = {
    "type": "function",
    "function": {
        "name": "local_delete",
        "description": "ลบไฟล์จาก Local Workspace บนเครื่อง user (ใช้เมื่ออยู่ใน Local Agent Mode เท่านั้น)",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "ชื่อไฟล์ที่ต้องการลบ"
                }
            },
            "required": ["filename"]
        }
    }
}

LOCAL_AGENT_TOOLS = [
    t for t in MCP_TOOLS if t['function']['name'] == 'web_search'
] + [_LOCAL_DELETE_TOOL]

def _tool_result_is_error(result: str) -> bool:
    """Return True when a tool result string represents a failure."""
    return result.strip().startswith('❌')


# ─── Confirmation Flow Helpers ───────────────────────

# Thai keywords: substring match is safe (Thai script has no ambiguous substring overlap)
# English keywords that risk substring false-positives ('ok' in 'stock', 'save' in 'unsaved')
# are handled via word-boundary regex instead.
_SAVE_KEYWORDS = {'บันทึก', 'เซฟ', 'ยืนยัน', 'ตกลง', 'ได้เลย', 'โอเค', 'บันทึกได้', 'บันทึกเลย', 'บันทึกได้เลย', 'ใช้ได้'}
_SAVE_BOUNDARY_RE = re.compile(r'\b(?:ok|save)\b', re.IGNORECASE)
_SAVE_NEGATIVE_PREFIX = {'ไม่ใช่', 'ไม่ใช้'}
_DISCARD_KEYWORDS = {'ยกเลิก', 'cancel', 'ไม่เอา', 'ไม่บันทึก', 'ไม่ต้องการ', 'ข้ามไป', 'ลบทิ้ง', 'discard'}
_EDIT_KEYWORDS = {'แก้ไข', 'แก้', 'ปรับ', 'ปรับปรุง', 'ปรับแก้', 'เพิ่ม', 'ลบ', 'เปลี่ยน', 'แทนที่', 'เพิ่มเติม', 'ตัดออก', 'แก้ตรง', 'ปรับตรง', 'edit', 'modify', 'update', 'change', 'fix', 'adjust', 'add', 'remove', 'delete', 'replace', 'revise'}

def _is_save_intent(message: str) -> bool:
    msg = message.lower().strip()
    if any(neg in msg for neg in _SAVE_NEGATIVE_PREFIX): return False
    return any(kw in msg for kw in _SAVE_KEYWORDS) or bool(_SAVE_BOUNDARY_RE.search(msg))

def _is_discard_intent(message: str) -> bool:
    return any(kw in message.lower().strip() for kw in _DISCARD_KEYWORDS)

def _is_pure_discard(message: str) -> bool:
    return message.lower().strip() in _DISCARD_KEYWORDS

def _is_edit_intent(message: str) -> bool:
    return any(kw in message.lower().strip() for kw in _EDIT_KEYWORDS)

def _suggest_filename(agent: str, content: str, fmt: str = 'md') -> str:
    ext = fmt if fmt in converter.SUPPORTED_FORMATS else 'md'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    m = re.search(r'#\s*(.{3,60})', content)
    if m:
        ascii_only = re.sub(r'[^\x20-\x7E]', ' ', m.group(1).strip())
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', ascii_only).strip('_')[:30]
        if len(slug) >= 3: return f"{agent}_{slug}_{ts}.{ext}"
    return f"{agent}_{ts}.{ext}"

def _write_temp(content: str, agent: str) -> str:
    filename = _suggest_filename(agent, content)
    temp_path = os.path.join(TEMP_DIR, filename)
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return temp_path

def _move_to_workspace(temp_path: str, workspace: str) -> str:
    import shutil
    filename = os.path.basename(temp_path)
    dest = os.path.join(workspace, filename)
    try: os.replace(temp_path, dest)
    except OSError: shutil.move(temp_path, dest)
    return filename

def _cleanup_old_temp():
    cutoff = datetime.now().timestamp() - 3600
    try:
        for fname in os.listdir(TEMP_DIR):
            if fname == '.gitkeep': continue
            fpath = os.path.join(TEMP_DIR, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
    except OSError as e:
        logger.warning(f"[cleanup_old_temp] could not clean temp dir: {e}")

def handle_save(pending_doc: str, pending_agent: str, workspace: str, job_id=None, output_format: str = 'md'):
    try:
        filename = _suggest_filename(pending_agent, pending_doc, output_format)
        yield format_sse({'type': 'status', 'message': f'กำลังบันทึกไฟล์ {filename}...'})
        if output_format in ('md', 'txt'):
            result = execute_tool(workspace, 'create_file', {'filename': filename, 'content': pending_doc})
            if _tool_result_is_error(result):
                yield format_sse({'type': 'save_failed', 'message': result})
                return
        else:
            file_bytes = converter.convert(pending_doc, output_format)
            with open(os.path.join(workspace, filename), 'wb') as f: f.write(file_bytes)
            result = f"บันทึก {filename} เรียบร้อย"
        size = len(pending_doc.encode('utf-8')) if output_format in ('md', 'txt') else os.path.getsize(os.path.join(workspace, filename))
        db.record_file(job_id, filename, pending_agent, size)
        _notify_workspace_changed(workspace)
        yield format_sse({'type': 'text', 'content': f'✅ {result}'})
        yield format_sse({'type': 'tool_result', 'tool': 'create_file', 'result': result})
    except Exception as e:
        logger.error(f"[handle_save] error: {e}", exc_info=True)
        yield format_sse({'type': 'save_failed', 'message': 'ไม่สามารถบันทึกไฟล์ได้ กรุณาลองใหม่อีกครั้ง'})

def handle_revise(pending_doc: str, pending_agent: str, instruction: str, history=None):
    agent_instance = AgentFactory.get_agent(pending_agent)
    yield {'type': 'agent', 'agent': pending_agent, 'reason': 'แก้ไขเอกสาร'}
    yield {'type': 'status', 'message': f'{agent_instance.name} กำลังแก้ไขเอกสาร...'}
    revise_message = (
        f"แก้ไขเอกสารต่อไปนี้ตามคำสั่งที่ได้รับ\n\n"
        f"คำสั่งแก้ไข: {instruction}\n\nเอกสารเดิม:\n{pending_doc}"
    )
    try:
        for chunk in agent_instance.stream_response(revise_message, history=history, max_tokens=10000):
            yield {'type': 'text', 'content': chunk}
    except Exception as e:
        logger.error(f"[handle_revise] stream_response error: {e}", exc_info=True)
        yield {'type': 'error', 'message': 'ไม่สามารถแก้ไขเอกสารได้ กรุณาลองใหม่อีกครั้ง'}

def _is_safe_temp_path(path: str) -> bool:
    try:
        resolved = os.path.realpath(os.path.abspath(path))
        return os.path.commonpath([resolved, TEMP_DIR]) == TEMP_DIR
    except (ValueError, TypeError):
        return False

def handle_pm_save(temp_paths: list, workspace: str, job_id=None, output_format: str = 'md', output_formats: list = None, agent_types: list = None):
    saved = []
    for i, temp_path in enumerate(temp_paths):
        fmt = (output_formats[i] if output_formats and i < len(output_formats) else output_format)
        if not _is_safe_temp_path(temp_path) or not os.path.isfile(temp_path): continue
        try:
            if fmt in ('md', 'txt'):
                filename = _move_to_workspace(temp_path, workspace)
                if fmt == 'txt' and filename.endswith('.md'):
                    new_name = filename[:-3] + '.txt'
                    os.rename(os.path.join(workspace, filename), os.path.join(workspace, new_name))
                    filename = new_name
            else:
                with open(temp_path, 'r', encoding='utf-8') as f: content = f.read()
                filename = f"{os.path.splitext(os.path.basename(temp_path))[0]}.{fmt}"
                with open(os.path.join(workspace, filename), 'wb') as f: f.write(converter.convert(content, fmt))
                os.remove(temp_path)
            saved.append(filename)
            size = os.path.getsize(os.path.join(workspace, filename))
            agent_type = (agent_types[i] if agent_types and i < len(agent_types) else filename.split('_')[0])
            db.record_file(job_id, filename, agent_type, size)
            _notify_workspace_changed(workspace)
            yield format_sse({'type': 'tool_result', 'tool': 'create_file', 'result': f'บันทึก {filename} เรียบร้อย'})
        except Exception as e:
            logger.error(f"[handle_pm_save] failed to save {os.path.basename(temp_path)}: {e}", exc_info=True)
            yield format_sse({'type': 'error', 'message': f'ไม่สามารถบันทึก {os.path.basename(temp_path)} กรุณาลองใหม่'})

    if saved:
        names_str = ", ".join(saved)
        msg_text = f"✅ บันทึก {len(saved)} ไฟล์เรียบร้อย\n{names_str}"
        yield format_sse({'type': 'text', 'content': msg_text})
    else:
        yield format_sse({'type': 'text', 'content': 'ไม่พบไฟล์ที่รอบันทึก'})

# ─── Routes ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000", "http://0.0.0.0:5000"])
db.init_db()

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    return jsonify({'error': 'คุณส่งคำสั่งบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่'}), 429

@app.route('/')
def index(): return send_file('index.html')

@app.route('/history')
def history_page(): return send_file('history.html')

@app.route('/api/chat', methods=['POST'])
@limiter.limit(os.getenv("CHAT_RATE_LIMIT", "10 per minute"))
def chat():
    if not request.json: return jsonify({'error': 'Invalid request'}), 400
    user_input = request.json.get('message', '').strip()
    if not user_input: return jsonify({'error': 'ไม่มีข้อความ'}), 400
    
    pending_doc = request.json.get('pending_doc', '').strip()[:_MAX_PENDING_DOC_BYTES]
    pending_agent = request.json.get('pending_agent', '').strip()
    pending_temp_paths = request.json.get('pending_temp_paths', [])
    pending_agent_types = request.json.get('agent_types') or []
    session_id = request.json.get('session_id')
    output_format = request.json.get('output_format', 'md').lower()
    output_formats = request.json.get('output_formats')
    local_agent_mode = bool(request.json.get('local_agent_mode', False))
    raw_history = request.json.get('conversation_history', [])

    conversation_history = [
        {'role': m['role'], 'content': str(m['content'])[:3000]}
        for m in (raw_history[-20:] if isinstance(raw_history, list) else [])
        if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and m.get('content')
    ]

    def generate():
        job_id = db.create_job(user_input, session_id)
        # Capture workspace once at request start — do NOT call get_workspace() again
        # inside the PM loop or sub-agent calls (D3: global state risk).
        workspace = get_workspace()
        os.makedirs(workspace, exist_ok=True)
        _cleanup_old_temp()

        if pending_temp_paths:
            if _is_save_intent(user_input):
                for sse in handle_pm_save(pending_temp_paths, workspace, job_id, output_format, output_formats, pending_agent_types): yield sse
                db.complete_job(job_id, '')
                yield format_sse({'type': 'done'})
                return
            if _is_edit_intent(user_input) and not _is_discard_intent(user_input):
                db.discard_job(job_id)
                yield format_sse({'type': 'text', 'content': 'คุณมีไฟล์รอบันทึกอยู่ กรุณาพิมพ์ **บันทึก** เพื่อบันทึกไฟล์ก่อน หรือ **ยกเลิก** เพื่อยกเลิกแล้วส่งคำสั่งใหม่'})
                yield format_sse({'type': 'done'})
                return
            for tp in pending_temp_paths:
                if _is_safe_temp_path(tp) and os.path.isfile(tp): os.remove(tp)
            if _is_pure_discard(user_input):
                db.discard_job(job_id)
                yield format_sse({'type': 'text', 'content': '🗑️ ยกเลิกการบันทึกไฟล์เรียบร้อย'})
                yield format_sse({'type': 'done'})
                return
            yield format_sse({'type': 'status', 'message': '🗑️ ยกเลิกไฟล์เก่าแล้ว กำลังดำเนินการคำสั่งใหม่...'})

        if pending_doc and pending_agent:
            if _is_save_intent(user_input):
                for sse in handle_save(pending_doc, pending_agent, workspace, job_id, output_format): yield sse
                db.complete_job(job_id, pending_doc)
                yield format_sse({'type': 'done'})
                return
            elif _is_discard_intent(user_input):
                if _is_pure_discard(user_input):
                    db.discard_job(job_id)
                    yield format_sse({'type': 'text', 'content': '🗑️ ยกเลิกเอกสารแล้ว สามารถส่งคำสั่งใหม่ได้เลย'})
                    yield format_sse({'type': 'done'})
                    return
                yield format_sse({'type': 'status', 'message': '🗑️ ยกเลิกเอกสารเดิมแล้ว กำลังดำเนินการคำสั่งใหม่...'})
            elif _is_edit_intent(user_input):
                text_chunks = []
                for event in handle_revise(pending_doc, pending_agent, user_input, history=conversation_history):
                    yield format_sse(event)
                    if event.get('type') == 'text':
                        text_chunks.append(event.get('content', ''))
                db.complete_job(job_id, ''.join(text_chunks))
                yield format_sse({'type': 'done'})
                return
            else:
                yield format_sse({'type': 'status', 'message': '🗑️ ยกเลิกเอกสารเดิมแล้ว กำลังดำเนินการคำสั่งใหม่...'})

        try:
            yield format_sse({'type': 'status', 'message': 'กำลังวิเคราะห์งาน...'})
            orch = Orchestrator()
            agent_type, reason = orch.route(user_input, conversation_history)
            db.update_job_agent(job_id, agent_type, reason)
            yield format_sse({'type': 'agent', 'agent': agent_type, 'reason': reason})

            agent_instance = AgentFactory.get_agent(agent_type)

            if agent_type == 'pm':
                yield format_sse({'type': 'status', 'message': 'PM Agent กำลังวางแผนงาน...'})
                subtasks = agent_instance.plan(user_input, conversation_history)
                if not subtasks:
                    yield format_sse({'type': 'error', 'message': 'PM Agent ไม่สามารถแบ่งงานได้'})
                    return
                yield format_sse({'type': 'pm_plan', 'subtasks': subtasks})
                
                all_pm_chunks = []
                for i, subtask in enumerate(subtasks):
                    sub_agent_type = subtask.get('agent', 'hr')
                    sub_task_desc = subtask.get('task', user_input)
                    sub_agent = AgentFactory.get_agent(sub_agent_type)
                    
                    yield format_sse({'type': 'agent', 'agent': sub_agent_type, 'reason': f'Subtask {i+1}/{len(subtasks)}', 'task': sub_task_desc[:80]})
                    yield format_sse({'type': 'status', 'message': f'{sub_agent.name} กำลังสร้างเอกสาร...'})
                    
                    subtask_chunks = []
                    try:
                        for chunk in sub_agent.stream_response(f"[PM_SUBTASK]\n{sub_task_desc}", max_tokens=10000):
                            yield format_sse({'type': 'text', 'content': chunk})
                            subtask_chunks.append(chunk)
                    except Exception as sub_e:
                        logger.error("[PM subtask %d] stream_response failed: %s", i + 1, sub_e, exc_info=True)
                        yield format_sse({'type': 'error', 'message': f'Subtask {i + 1} ({sub_agent.name}) เกิดข้อผิดพลาด: กรุณาลองใหม่อีกครั้ง'})
                        yield format_sse({'type': 'subtask_done', 'agent': sub_agent_type, 'index': i, 'total': len(subtasks)})
                        continue

                    # Strip sentinel echo and save-footer in case LLM ignores prompt rule
                    _SAVE_FOOTER = '💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์'
                    full_content = ''.join(subtask_chunks).replace('[PM_SUBTASK]', '').replace(_SAVE_FOOTER, '').strip()
                    all_pm_chunks.append(full_content)
                    if full_content.strip():
                        temp_path = _write_temp(full_content, sub_agent_type)
                        yield format_sse({'type': 'pending_file', 'temp_path': temp_path, 'filename': os.path.basename(temp_path), 'agent': sub_agent_type})
                    yield format_sse({'type': 'subtask_done', 'agent': sub_agent_type, 'index': i, 'total': len(subtasks)})
                
                db.complete_job(job_id, '\n\n---\n\n'.join(all_pm_chunks))
            else:
                yield format_sse({'type': 'status', 'message': f'{agent_instance.name} กำลังตรวจสอบ workspace...'})
                active_tools = LOCAL_AGENT_TOOLS if local_agent_mode else READ_ONLY_TOOLS
                text_chunks = []
                for sse_data in agent_instance.run_with_tools(user_input, workspace, tools=active_tools, history=conversation_history, max_tokens=10000):
                    # Intercept local_delete marker — ส่ง event ให้ browser ลบจริง
                    if (sse_data.get('type') == 'tool_result'
                            and sse_data.get('tool') == 'local_delete'
                            and sse_data.get('result', '').startswith('__LOCAL_DELETE__:')):
                        filename = sse_data['result'].split(':', 1)[1]
                        yield format_sse({'type': 'local_delete', 'filename': filename})
                    else:
                        yield format_sse(sse_data)
                    if sse_data.get('type') == 'text': text_chunks.append(sse_data.get('content', ''))
                db.complete_job(job_id, ''.join(text_chunks))

            yield format_sse({'type': 'done'})
        except Exception as e:
            db.fail_job(job_id)
            logger.error(f"[generate] unhandled error: {e}", exc_info=True)
            yield format_sse({'type': 'error', 'message': 'เกิดข้อผิดพลาดจากระบบ กรุณาลองใหม่อีกครั้ง'})
            yield format_sse({'type': 'done'})

    return Response(stream_with_context(generate()), mimetype='text/event-stream; charset=utf-8', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})

@app.route('/api/workspace', methods=['GET'])
def get_workspace_api():
    wp = get_workspace()
    return jsonify({'path': wp, 'exists': os.path.isdir(wp), 'files': len(fs_list_files(wp))})

@app.route('/api/workspace', methods=['POST'])
def set_workspace_api():
    new_path = (request.json or {}).get('path', '').strip()
    abs_path = _normalize_workspace_path(new_path)
    if len(abs_path) <= 3 or not _is_allowed_workspace_path(abs_path): return jsonify({'error': 'Invalid path'}), 400
    os.makedirs(abs_path, exist_ok=True)
    set_workspace(abs_path)
    return jsonify({'path': abs_path, 'exists': True})

@app.route('/api/workspaces', methods=['GET'])
def list_workspaces():
    current = os.path.realpath(get_workspace())
    result = {'current': current, 'roots': []}
    for root in _ALLOWED_ROOTS:
        workspaces = []
        try:
            for entry in sorted(os.scandir(root), key=lambda e: e.name.lower()):
                if entry.is_dir() and not entry.name.startswith('.'):
                    workspaces.append({'path': entry.path, 'name': entry.name, 'active': os.path.realpath(entry.path) == current})
        except OSError as e:
            logger.warning(f"[list_workspaces] cannot scan root {root}: {e}")
        result['roots'].append({'root': root, 'label': os.path.basename(root) or root, 'workspaces': workspaces})
    return jsonify(result)

@app.route('/api/workspace/new', methods=['POST'])
def create_workspace_folder():
    data = request.json or {}
    root, name = data.get('root', '').strip(), data.get('name', '').strip()
    if not root or not name or not re.match(r'^[a-zA-Z0-9_-]{1,50}$', name): return jsonify({'error': 'Invalid request'}), 400
    new_path = os.path.realpath(os.path.join(root, name))
    os.makedirs(new_path, exist_ok=True)
    set_workspace(new_path)
    return jsonify({'path': new_path, 'name': name})

@app.route('/api/files')
def list_files_snapshot():
    wp = get_workspace()
    return jsonify({'workspace': wp, 'files': fs_list_files(wp)})

@app.route('/api/files/stream')
def files_stream():
    def generate():
        wp = get_workspace()
        event_queue = queue.Queue(maxsize=20)
        with _ws_change_lock: _ws_change_queues.setdefault(wp, []).append(event_queue)
        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                if not event.is_directory:
                    try: event_queue.put_nowait('changed')
                    except queue.Full: pass
        observer = Observer()
        observer.schedule(Handler(), wp, recursive=False)
        observer.start()
        try:
            yield format_sse({'type': 'files', 'files': fs_list_files(wp), 'workspace': wp})
            while True:
                try: event_queue.get(timeout=25)
                except queue.Empty:
                    yield format_sse({'type': 'heartbeat'})
                    continue
                yield format_sse({'type': 'files', 'files': fs_list_files(wp), 'workspace': wp})
        finally:
            observer.stop()
            observer.join(timeout=2)
            with _ws_change_lock:
                bucket = _ws_change_queues.get(wp, [])
                if event_queue in bucket: bucket.remove(event_queue)
    return Response(stream_with_context(generate()), mimetype='text/event-stream; charset=utf-8', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})

@app.route('/api/health')
def health():
    wp = get_workspace()
    return jsonify({'status': 'ok', 'model': MODEL, 'workspace': wp, 'db': db.db_status()})

@app.route('/api/history')
def history(): return jsonify({'jobs': db.get_history(int(request.args.get('limit', 50))), 'db_available': db.DB_AVAILABLE})

@app.route('/api/history/<job_id>')
def history_job(job_id: str):
    job = db.get_job(job_id)
    return jsonify(job) if job else (jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG','').lower() in {'1','true'}, host=os.getenv('FLASK_HOST','0.0.0.0'), port=5000, threaded=True)
