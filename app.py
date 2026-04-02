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
    MODEL, OPENROUTER_API_KEY, _ALLOWED_ROOTS,
    _DEFAULT_WORKSPACE, _workspace_lock, _ws_change_queues, _ws_change_lock,
    TEMP_DIR, _notify_workspace_changed, get_workspace, get_session_workspace, set_workspace, set_session_workspace,
    remove_session_workspace,
    AGENT_MAX_TOKENS, CHAT_MAX_TOKENS
)
from core.utils import load_prompt, execute_tool, format_sse
from core.orchestrator import Orchestrator
from core.agent_factory import AgentFactory

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_MAX_PENDING_DOC_BYTES = int(os.getenv('MAX_PENDING_DOC_BYTES', str(200 * 1024)))  # 200KB default


def _truncate_at_word(text: str, max_len: int) -> str:
    """Truncate text at a word boundary to avoid cutting mid-sentence or mid-JSON."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.8:
        return truncated[:last_space] + '…'
    return truncated + '…'


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


_SESSION_ID_RE = re.compile(r'^[\w\-]{8,64}$')


def _get_request_session_id() -> str | None:
    """Read and validate session_id from query string or JSON body."""
    session_id = (request.args.get('session_id') or '').strip()
    if not session_id and request.is_json:
        payload = request.get_json(silent=True) or {}
        session_id = str(payload.get('session_id') or '').strip()
    if not session_id:
        return None
    if not _SESSION_ID_RE.match(session_id):
        return None
    return session_id


def _has_invalid_request_session_id() -> bool:
    """Return True when a session_id was provided but failed validation."""
    query_session_id = (request.args.get('session_id') or '').strip()
    body_session_id = ''
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        body_session_id = str(payload.get('session_id') or '').strip()
    raw_session_id = query_session_id or body_session_id
    return bool(raw_session_id and not _SESSION_ID_RE.match(raw_session_id))


def _get_request_workspace() -> str:
    """Resolve workspace for the current request, preferring session scope."""
    session_id = _get_request_session_id()
    return get_session_workspace(session_id) if session_id else get_workspace()

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
    },
    {
        "type": "function",
        "function": {
            "name": "request_delete",
            "description": (
                "ส่งคำขอลบไฟล์จาก workspace โดยต้องรอให้ผู้ใช้ยืนยันก่อน "
                "ห้ามใช้ delete_file โดยตรง — ใช้ request_delete เสมอเมื่อต้องการลบไฟล์"
            ),
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
]

READ_ONLY_TOOLS = [t for t in MCP_TOOLS if t['function']['name'] in ('list_files', 'read_file', 'web_search', 'request_delete')]

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
# NOTE: _is_save_intent is only called when pending_doc or pending_temp_paths exists
# (guarded by outer if-blocks in chat()), so false positives are mitigated.
_SAVE_KEYWORDS = {'บันทึก', 'เซฟ', 'ยืนยัน', 'ตกลง', 'ได้เลย', 'โอเค', 'บันทึกได้', 'บันทึกเลย', 'บันทึกได้เลย', 'ใช้ได้'}
_SAVE_BOUNDARY_RE = re.compile(r'\b(?:ok|save)\b', re.IGNORECASE)
_SAVE_NEGATIVE_PREFIX = {'ไม่ใช่', 'ไม่ใช้'}
_DISCARD_KEYWORDS = {'ยกเลิก', 'cancel', 'ไม่เอา', 'ไม่บันทึก', 'ไม่ต้องการ', 'ข้ามไป', 'ลบทิ้ง', 'discard'}
_EDIT_KEYWORDS = {'แก้ไข', 'แก้', 'ปรับ', 'ปรับปรุง', 'ปรับแก้', 'เพิ่ม', 'ลบ', 'เปลี่ยน', 'แทนที่', 'เพิ่มเติม', 'ตัดออก', 'แก้ตรง', 'ปรับตรง', 'edit', 'modify', 'update', 'change', 'fix', 'adjust', 'add', 'remove', 'delete', 'replace', 'revise'}
_VALID_FORMATS = {'md', 'txt', 'docx', 'xlsx', 'pdf'}

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

def _suggest_filename(agent: str, content: str, fmt: str = 'md', history: list = None) -> str:
    ext = fmt if fmt in converter.SUPPORTED_FORMATS else 'md'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 1. Try heading from document content
    m = re.search(r'#\s*(.{3,60})', content)
    if m:
        ascii_only = re.sub(r'[^\x20-\x7E]', ' ', m.group(1).strip())
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', ascii_only).strip('_')[:30]
        if len(slug) >= 3: return f"{agent}_{slug}_{ts}.{ext}"
    # 2. Fallback: use last user message from history for context
    if history:
        for msg in reversed(history[-5:]):
            if msg.get('role') == 'user' and msg.get('content'):
                ascii_only = re.sub(r'[^\x20-\x7E]', ' ', str(msg['content'])[:80])
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

def handle_save(pending_doc: str, pending_agent: str, workspace: str, job_id=None, output_format: str = 'md', history: list = None, overwrite_filename: str = None, local_agent_mode: bool = False):
    """Yields raw event dicts (not pre-formatted SSE) so callers can inspect type.
    If overwrite_filename is set, update the existing file instead of creating a new one."""
    if local_agent_mode:
        yield {'type': 'save_failed', 'message': 'โหมด Local Agent ไม่รองรับการบันทึกไฟล์ — กรุณาปิดโหมด Local Agent ก่อน'}
        return
    try:
        if overwrite_filename:
            filename = overwrite_filename
            tool_name = 'update_file'
            # When overwriting, infer format from the existing file's extension
            # so a .docx is re-converted properly instead of receiving raw markdown text
            _ext = os.path.splitext(filename)[1].lower().lstrip('.')
            if _ext in ('docx', 'pdf'):
                output_format = _ext
        else:
            filename = _suggest_filename(pending_agent, pending_doc, output_format, history)
            tool_name = 'create_file'
        yield {'type': 'status', 'message': f'กำลังบันทึกไฟล์ {filename}...'}
        if output_format in ('md', 'txt'):
            result = execute_tool(workspace, tool_name, {'filename': filename, 'content': pending_doc})
            if _tool_result_is_error(result):
                yield {'type': 'save_failed', 'message': result}
                return
        else:
            file_bytes = converter.convert(pending_doc, output_format)
            with open(os.path.join(workspace, filename), 'wb') as f: f.write(file_bytes)
            result = f"บันทึก {filename} เรียบร้อย"
        size = len(pending_doc.encode('utf-8')) if output_format in ('md', 'txt') else os.path.getsize(os.path.join(workspace, filename))
        db.record_file(job_id, filename, pending_agent, size)
        _notify_workspace_changed(workspace)
        yield {'type': 'text', 'content': f'✅ {result}'}
        yield {'type': 'tool_result', 'tool': tool_name, 'result': result}
    except Exception as e:
        logger.error(f"[handle_save] error: {e}", exc_info=True)
        yield {'type': 'save_failed', 'message': 'ไม่สามารถบันทึกไฟล์ได้ กรุณาลองใหม่อีกครั้ง'}

def handle_revise(pending_doc: str, pending_agent: str, instruction: str, history=None):
    agent_instance = AgentFactory.get_agent(pending_agent)
    yield {'type': 'agent', 'agent': pending_agent, 'reason': 'แก้ไขเอกสาร'}
    yield {'type': 'status', 'message': f'{agent_instance.name} กำลังแก้ไขเอกสาร...'}
    revise_message = (
        f"แก้ไขเอกสารต่อไปนี้ตามคำสั่งที่ได้รับ\n\n"
        f"คำสั่งแก้ไข: {instruction}\n\nเอกสารเดิม:\n{pending_doc}"
    )
    try:
        for chunk in agent_instance.stream_response(revise_message, history=history, max_tokens=AGENT_MAX_TOKENS):
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
    """Yields raw event dicts (not pre-formatted SSE) so callers can inspect type."""
    saved = []
    for i, temp_path in enumerate(temp_paths):
        fmt = (output_formats[i] if output_formats and i < len(output_formats) else output_format)
        if not _is_safe_temp_path(temp_path) or not os.path.isfile(temp_path):
            logger.warning("[handle_pm_save] skipped unsafe or missing temp path: %s", temp_path)
            yield {'type': 'error', 'message': f'ข้ามไฟล์ที่ไม่ปลอดภัยหรือไม่มีอยู่: {os.path.basename(temp_path)}'}
            continue
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
            yield {'type': 'tool_result', 'tool': 'create_file', 'result': f'บันทึก {filename} เรียบร้อย'}
        except Exception as e:
            logger.error(f"[handle_pm_save] failed to save {os.path.basename(temp_path)}: {e}", exc_info=True)
            yield {'type': 'error', 'message': f'ไม่สามารถบันทึก {os.path.basename(temp_path)} กรุณาลองใหม่'}

    if saved:
        names_str = ", ".join(saved)
        yield {'type': 'text', 'content': f'✅ บันทึก {len(saved)} ไฟล์เรียบร้อย\n{names_str}'}
    else:
        yield {'type': 'text', 'content': 'ไม่พบไฟล์ที่รอบันทึก'}

# ─── Routes ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.json.ensure_ascii = False
_cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000,http://0.0.0.0:5000')
CORS(app, origins=[o.strip() for o in _cors_origins.split(',') if o.strip()])
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
    
    _raw_doc = request.json.get('pending_doc', '').strip()
    pending_doc = _raw_doc.encode('utf-8')[:_MAX_PENDING_DOC_BYTES].decode('utf-8', errors='ignore')
    pending_agent = request.json.get('pending_agent', '').strip()
    _raw_paths = request.json.get('pending_temp_paths', [])
    pending_temp_paths = [
        str(p) for p in _raw_paths
        if isinstance(p, str) and p.strip()
    ] if isinstance(_raw_paths, list) else []
    pending_agent_types = request.json.get('agent_types') or []
    session_id = request.json.get('session_id')
    output_format = str(request.json.get('output_format', 'md')).lower().strip()
    if output_format not in _VALID_FORMATS:
        output_format = 'md'
    _raw_output_formats = request.json.get('output_formats')
    output_formats = [
        fmt if fmt in _VALID_FORMATS else output_format
        for fmt in (
            str(item).lower().strip()
            for item in _raw_output_formats
            if isinstance(item, str) and item.strip()
        )
    ] if isinstance(_raw_output_formats, list) else None
    _raw_overwrite = (request.json.get('overwrite_filename') or '').strip()
    overwrite_filename = _raw_overwrite if _raw_overwrite and re.match(r'^[\w.\-]{1,120}$', _raw_overwrite) else None
    if _raw_overwrite and not overwrite_filename:
        logger.warning("[chat] rejected invalid overwrite_filename: %r", _raw_overwrite[:80])
    local_agent_mode = bool(request.json.get('local_agent_mode', False))
    raw_history = request.json.get('conversation_history', [])

    conversation_history = [
        {'role': m['role'], 'content': _truncate_at_word(str(m['content']), 3000)}
        for m in (raw_history[-20:] if isinstance(raw_history, list) else [])
        if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and m.get('content')
    ]

    def generate():
        job_id = db.create_job(user_input, session_id)
        _job_completed = False
        _job_failed = False
        # Capture workspace once at request start — do NOT call get_workspace() again
        # inside the PM loop or sub-agent calls (D3: global state risk).
        workspace = get_session_workspace(session_id) if session_id else get_workspace()
        os.makedirs(workspace, exist_ok=True)
        _cleanup_old_temp()

        if pending_temp_paths:
            if _is_save_intent(user_input):
                pm_save_ok = True
                for event in handle_pm_save(pending_temp_paths, workspace, job_id, output_format, output_formats, pending_agent_types):
                    yield format_sse(event)
                    if event.get('type') == 'error':
                        pm_save_ok = False
                if pm_save_ok:
                    db.complete_job(job_id, '')
                    _job_completed = True
                else:
                    db.fail_job(job_id)
                yield format_sse({'type': 'done'})
                return
            if _is_edit_intent(user_input) and not _is_discard_intent(user_input):
                yield format_sse({'type': 'text', 'content': 'คุณมีไฟล์รอบันทึกอยู่ กรุณาพิมพ์ **บันทึก** เพื่อบันทึกไฟล์ก่อน หรือ **ยกเลิก** เพื่อยกเลิกแล้วส่งคำสั่งใหม่'})
                yield format_sse({'type': 'done'})
                return
            for tp in pending_temp_paths:
                if _is_safe_temp_path(tp) and os.path.isfile(tp): os.remove(tp)
            if _is_pure_discard(user_input):
                db.discard_job(job_id)
                _job_completed = True
                yield format_sse({'type': 'text', 'content': '🗑️ ยกเลิกการบันทึกไฟล์เรียบร้อย'})
                yield format_sse({'type': 'done'})
                return
            yield format_sse({'type': 'status', 'message': '🗑️ ยกเลิกไฟล์เก่าแล้ว กำลังดำเนินการคำสั่งใหม่...'})

        if pending_doc and pending_agent:
            if _is_save_intent(user_input):
                save_ok = True
                for event in handle_save(pending_doc, pending_agent, workspace, job_id, output_format, conversation_history[-5:], overwrite_filename, local_agent_mode=local_agent_mode):
                    yield format_sse(event)
                    if event.get('type') == 'save_failed':
                        save_ok = False
                if save_ok:
                    db.complete_job(job_id, pending_doc)
                    _job_completed = True
                else:
                    db.fail_job(job_id)
                yield format_sse({'type': 'done'})
                return
            elif _is_discard_intent(user_input):
                if _is_pure_discard(user_input):
                    db.discard_job(job_id)
                    _job_completed = True
                    yield format_sse({'type': 'text', 'content': '🗑️ ยกเลิกเอกสารแล้ว สามารถส่งคำสั่งใหม่ได้เลย'})
                    yield format_sse({'type': 'done'})
                    return
                yield format_sse({'type': 'status', 'message': '🗑️ ยกเลิกเอกสารเดิมแล้ว กำลังดำเนินการคำสั่งใหม่...'})
            elif _is_edit_intent(user_input):
                text_chunks = []
                revise_ok = True
                for event in handle_revise(pending_doc, pending_agent, user_input, history=conversation_history):
                    yield format_sse(event)
                    if event.get('type') == 'text':
                        text_chunks.append(event.get('content', ''))
                    elif event.get('type') == 'error':
                        revise_ok = False
                if revise_ok:
                    db.complete_job(job_id, ''.join(text_chunks))
                    _job_completed = True
                else:
                    db.fail_job(job_id)
                    _job_failed = True
                yield format_sse({'type': 'done'})
                return
            else:
                yield format_sse({'type': 'status', 'message': '🗑️ ยกเลิกเอกสารเดิมแล้ว กำลังดำเนินการคำสั่งใหม่...'})

        try:
            yield format_sse({'type': 'status', 'message': 'กำลังวิเคราะห์งาน...'})
            orch = Orchestrator()
            agent_type, reason = orch.route(user_input, conversation_history[-3:])
            db.update_job_agent(job_id, agent_type, reason)
            yield format_sse({'type': 'agent', 'agent': agent_type, 'reason': reason})

            agent_instance = AgentFactory.get_agent(agent_type)

            if agent_type == 'pm':
                yield format_sse({'type': 'status', 'message': 'PM Agent กำลังวางแผนงาน...'})
                subtasks = agent_instance.plan(user_input, conversation_history)
                if not subtasks:
                    yield format_sse({'type': 'error', 'message': 'PM Agent ไม่สามารถแบ่งงานได้'})
                    yield format_sse({'type': 'done'})
                    return
                yield format_sse({'type': 'pm_plan', 'subtasks': subtasks})

                all_pm_chunks = []
                pm_temp_paths = []
                pm_all_ok = True
                for i, subtask in enumerate(subtasks):
                    sub_agent_type = subtask.get('agent', 'hr')
                    sub_task_desc = subtask.get('task', user_input)
                    sub_agent = AgentFactory.get_agent(sub_agent_type)

                    yield format_sse({'type': 'agent', 'agent': sub_agent_type, 'reason': f'Subtask {i+1}/{len(subtasks)}', 'task': sub_task_desc[:80]})
                    yield format_sse({'type': 'status', 'message': f'{sub_agent.name} กำลังสร้างเอกสาร...'})

                    subtask_chunks = []
                    try:
                        for chunk in sub_agent.stream_response(f"[PM_SUBTASK]\n{sub_task_desc}", max_tokens=AGENT_MAX_TOKENS):
                            yield format_sse({'type': 'text', 'content': chunk})
                            subtask_chunks.append(chunk)
                    except Exception as sub_e:
                        pm_all_ok = False
                        logger.error("[PM subtask %d] stream_response failed: %s", i + 1, sub_e, exc_info=True)
                        yield format_sse({'type': 'error', 'message': f'Subtask {i + 1} ({sub_agent.name}) เกิดข้อผิดพลาด: กรุณาลองใหม่อีกครั้ง'})
                        yield format_sse({'type': 'subtask_done', 'agent': sub_agent_type, 'index': i, 'total': len(subtasks)})
                        for tp in pm_temp_paths:
                            try:
                                if os.path.isfile(tp): os.remove(tp)
                            except OSError: pass
                        break

                    # Strip sentinel echo and save-footer in case LLM ignores prompt rule
                    _SAVE_FOOTER = '💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์'
                    full_content = ''.join(subtask_chunks).replace('[PM_SUBTASK]', '').replace(_SAVE_FOOTER, '').strip()
                    all_pm_chunks.append(full_content)
                    if full_content.strip():
                        temp_path = _write_temp(full_content, sub_agent_type)
                        pm_temp_paths.append(temp_path)
                        yield format_sse({'type': 'pending_file', 'temp_path': temp_path, 'filename': os.path.basename(temp_path), 'agent': sub_agent_type})
                    yield format_sse({'type': 'subtask_done', 'agent': sub_agent_type, 'index': i, 'total': len(subtasks)})

                if pm_all_ok:
                    db.complete_job(job_id, '\n\n---\n\n'.join(all_pm_chunks))
                    _job_completed = True
                else:
                    db.fail_job(job_id)
                    _job_failed = True
            else:
                yield format_sse({'type': 'status', 'message': f'{agent_instance.name} กำลังตรวจสอบ workspace...'})
                active_tools = LOCAL_AGENT_TOOLS if local_agent_mode else READ_ONLY_TOOLS
                text_chunks = []
                _max_tok = CHAT_MAX_TOKENS if agent_type == 'chat' else AGENT_MAX_TOKENS
                for sse_data in agent_instance.run_with_tools(user_input, workspace, tools=active_tools, history=conversation_history, max_tokens=_max_tok):
                    # Intercept local_delete marker — ส่ง event ให้ browser ลบจริง
                    if (sse_data.get('type') == 'tool_result'
                            and sse_data.get('tool') == 'local_delete'
                            and sse_data.get('result', '').startswith('__LOCAL_DELETE__:')):
                        filename = sse_data['result'].split(':', 1)[1]
                        yield format_sse({'type': 'local_delete', 'filename': filename})
                    # Intercept request_delete marker — ส่ง event ให้ browser แสดง confirm modal
                    elif (sse_data.get('type') == 'tool_result'
                            and sse_data.get('tool') == 'request_delete'
                            and sse_data.get('result', '').startswith('__DELETE_REQUEST__:')):
                        filename = sse_data['result'].split(':', 1)[1].strip()
                        if filename:
                            yield format_sse({'type': 'delete_request', 'filename': filename})
                        else:
                            logger.warning("[generate] request_delete returned empty filename — suppressed")
                    else:
                        yield format_sse(sse_data)
                    if sse_data.get('type') == 'text': text_chunks.append(sse_data.get('content', ''))
                db.complete_job(job_id, ''.join(text_chunks))
                _job_completed = True

            yield format_sse({'type': 'done'})
        except Exception as e:
            db.fail_job(job_id)
            _job_failed = True
            logger.error(f"[generate] unhandled error: {e}", exc_info=True)
            yield format_sse({'type': 'error', 'message': 'เกิดข้อผิดพลาดจากระบบ กรุณาลองใหม่อีกครั้ง'})
            yield format_sse({'type': 'done'})
        finally:
            if not _job_completed and not _job_failed:
                db.fail_job(job_id)

    return Response(stream_with_context(generate()), mimetype='text/event-stream; charset=utf-8', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})

@app.route('/api/health')
def health():
    if _has_invalid_request_session_id():
        return jsonify({'error': 'invalid session_id'}), 400
    wp = _get_request_workspace()
    return jsonify({'status': 'ok', 'model': MODEL, 'workspace': wp, 'db': db.db_status()})

@app.route('/api/history')
def history():
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 200))
    except (ValueError, TypeError):
        limit = 50
    return jsonify({'jobs': db.get_history(limit), 'db_available': db.DB_AVAILABLE})

@app.route('/api/history/<job_id>')
def history_job(job_id: str):
    job = db.get_job(job_id)
    return jsonify(job) if job else (jsonify({'error': 'Not found'}), 404)

@app.route('/api/serve/<filename>')
def serve_workspace_file(filename: str):
    """Serve a raw file from the current workspace (used for PDF/image inline preview)."""
    if not re.match(r'^[\w.\-]{1,200}$', filename):
        return jsonify({'error': 'invalid filename'}), 400
    if _has_invalid_request_session_id():
        return jsonify({'error': 'invalid session_id'}), 400
    workspace = _get_request_workspace()
    filepath = os.path.join(workspace, filename)
    real_workspace = os.path.realpath(workspace)
    real_filepath = os.path.realpath(filepath)
    if not real_filepath.startswith(real_workspace + os.sep) and real_filepath != real_workspace:
        return jsonify({'error': 'access denied'}), 403
    if not os.path.isfile(filepath):
        return jsonify({'error': 'not found'}), 404
    return send_file(filepath, conditional=True, max_age=60)


@app.route('/api/preview')
def preview_file():
    filename = (request.args.get('file') or '').strip()
    if not filename or not re.match(r'^[\w.\-]{1,200}$', filename):
        return jsonify({'error': 'invalid filename'}), 400
    if _has_invalid_request_session_id():
        return jsonify({'error': 'invalid session_id'}), 400
    workspace = _get_request_workspace()
    filepath = os.path.join(workspace, filename)
    real_workspace = os.path.realpath(workspace)
    real_filepath = os.path.realpath(filepath)
    if not real_filepath.startswith(real_workspace + os.sep) and real_filepath != real_workspace:
        return jsonify({'error': 'access denied'}), 403
    if not os.path.isfile(filepath):
        return jsonify({'error': 'not found'}), 404
    try:
        content = fs_read_file(workspace, filename)
        ext = os.path.splitext(filename)[1].lower()
        size = os.path.getsize(filepath)
        return jsonify({'filename': filename, 'content': content, 'ext': ext, 'size': size})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete', methods=['POST'])
@limiter.limit("20 per minute")
def delete_file_api():
    data = request.json or {}
    filename = (data.get('filename') or '').strip()
    if not filename or not re.match(r'^[\w.\-]{1,120}$', filename):
        return jsonify({'error': 'invalid filename'}), 400
    session_id = _get_request_session_id()
    if data.get('session_id') and not session_id:
        return jsonify({'error': 'invalid session_id'}), 400
    workspace = get_session_workspace(session_id) if session_id else get_workspace()
    result = execute_tool(workspace, 'delete_file', {'filename': filename})
    if _tool_result_is_error(result):
        return jsonify({'error': result}), 400
    logger.info("[delete_file_api] deleted: %s from workspace %s", filename, workspace)
    _notify_workspace_changed(workspace)
    return jsonify({'success': True, 'filename': filename})


@app.route('/api/sessions')
def list_sessions():
    return jsonify({'sessions': db.get_sessions()})


@app.route('/api/sessions/<session_id>')
def get_session_api(session_id: str):
    if not _SESSION_ID_RE.match(session_id):
        return jsonify({'error': 'invalid session_id'}), 400
    return jsonify({'jobs': db.get_session_jobs(session_id)})


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session_api(session_id: str):
    if not _SESSION_ID_RE.match(session_id):
        return jsonify({'error': 'invalid session_id'}), 400

    deleted = db.delete_session(session_id)
    if not deleted:
        return jsonify({'error': 'ไม่พบเซสชันที่ต้องการลบ'}), 404

    remove_session_workspace(session_id)
    return jsonify({'success': True, 'session_id': session_id})


# ─── Workspace & File Management Routes ──────────────────────────────────────

@app.route('/api/files')
def api_list_files():
    """Return list of files in the current workspace."""
    if _has_invalid_request_session_id():
        return jsonify({'error': 'invalid session_id'}), 400
    workspace = _get_request_workspace()
    files = fs_list_files(workspace)
    return jsonify({'files': files})


@app.route('/api/files/stream')
def api_stream_files():
    """SSE endpoint — subscribe to workspace change notifications."""
    if _has_invalid_request_session_id():
        return jsonify({'error': 'invalid session_id'}), 400
    workspace = _get_request_workspace()

    def generate():
        q = queue.Queue()
        with _ws_change_lock:
            _ws_change_queues.setdefault(workspace, []).append(q)
        try:
            while True:
                try:
                    q.get(timeout=30)
                    yield format_sse({'type': 'files_changed'})
                except queue.Empty:
                    yield format_sse({'type': 'heartbeat'})
        except GeneratorExit:
            raise
        finally:
            with _ws_change_lock:
                queues = _ws_change_queues.get(workspace, [])
                if q in queues:
                    queues.remove(q)

    return Response(stream_with_context(generate()), mimetype='text/event-stream; charset=utf-8', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})


@app.route('/api/workspace')
def api_get_workspace():
    """Return the current workspace path."""
    if _has_invalid_request_session_id():
        return jsonify({'error': 'invalid session_id'}), 400
    return jsonify({'workspace': _get_request_workspace()})


@app.route('/api/workspace', methods=['POST'])
def api_set_workspace():
    """Set the workspace path. Validates against allowed roots."""
    if not request.json:
        return jsonify({'error': 'Invalid request'}), 400
    path = request.json.get('path', '').strip()
    if not path:
        return jsonify({'error': 'ต้องระบุ path'}), 400
    normalized = _normalize_workspace_path(path)
    if not _is_allowed_workspace_path(normalized):
        return jsonify({'error': f'ไม่อนุญาต: path อยู่นอก allowed roots'}), 400
    os.makedirs(normalized, exist_ok=True)
    session_id = str(request.json.get('session_id') or '').strip()
    if session_id and not _SESSION_ID_RE.match(session_id):
        return jsonify({'error': 'invalid session_id'}), 400
    if session_id:
        set_session_workspace(session_id, normalized)
    else:
        logger.warning("[api_set_workspace] no session_id provided — falling back to global workspace")
        set_workspace(normalized)
    return jsonify({'workspace': normalized}), 200


@app.route('/api/workspaces')
def api_list_workspaces():
    """List available workspace directories under allowed roots."""
    workspaces = []
    for root in _ALLOWED_ROOTS:
        if os.path.isdir(root):
            try:
                for entry in sorted(os.scandir(root), key=lambda e: e.name):
                    if entry.is_dir():
                        workspaces.append({
                            'name': entry.name,
                            'path': os.path.realpath(entry.path),
                        })
            except OSError:
                pass
    return jsonify({'workspaces': workspaces})


@app.route('/api/workspace/new', methods=['POST'])
def api_create_workspace():
    """Create a new workspace directory and set it as current."""
    if not request.json:
        return jsonify({'error': 'Invalid request'}), 400
    name = request.json.get('name', '').strip()
    if not name or not re.match(r'^[\w]{1,60}$', name):
        return jsonify({'error': 'ชื่อ workspace ต้องเป็นตัวอักษร a-z, 0-9 หรือ _ เท่านั้น (สูงสุด 60 ตัวอักษร)'}), 400
    base = os.path.dirname(_DEFAULT_WORKSPACE)
    new_path = os.path.join(base, name)
    if not _is_allowed_workspace_path(new_path):
        return jsonify({'error': f'ไม่อนุญาต: path อยู่นอก allowed roots'}), 400
    os.makedirs(new_path, exist_ok=True)
    session_id = str(request.json.get('session_id') or '').strip()
    if session_id and not _SESSION_ID_RE.match(session_id):
        return jsonify({'error': 'invalid session_id'}), 400
    if session_id:
        set_session_workspace(session_id, new_path)
    else:
        logger.warning("[api_create_workspace] no session_id provided — falling back to global workspace")
        set_workspace(new_path)
    return jsonify({'workspace': new_path}), 201


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG','').lower() in {'1','true'}, host=os.getenv('FLASK_HOST','0.0.0.0'), port=5000, threaded=True)
