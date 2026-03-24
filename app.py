from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from openai import OpenAI, RateLimitError, APITimeoutError, APIError
from dotenv import load_dotenv
from mcp_server import fs_list_files, fs_create_file, fs_read_file, fs_update_file, fs_delete_file
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json
import logging
import os
import re
import threading
import queue
from datetime import datetime

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> str:
    """Extract JSON from LLM output that may have markdown fences or surrounding prose.
    Strips ```...``` fences (any language tag), then slices from first { to last }.
    Raises ValueError if no JSON object found."""
    # Remove all code fence variants: ```json, ```JSON, ```javascript, ``` etc.
    cleaned = re.sub(r'```[^\n]*\n?', '', raw)
    cleaned = cleaned.replace('```', '').strip()
    # Slice to outermost braces
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in LLM output: {raw[:200]!r}")
    return cleaned[start:end + 1]

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError(
        "❌ ไม่พบ OPENROUTER_API_KEY ใน environment variables\n"
        "กรุณาสร้างไฟล์ .env และใส่ API key (ดูตัวอย่างใน .env.example)"
    )

MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")

# Workspace state — mutable at runtime via /api/workspace
_DEFAULT_WORKSPACE = os.path.abspath(
    os.getenv("WORKSPACE_PATH", os.path.join(os.path.dirname(__file__), "workspace"))
)
WORKSPACE_PATH = _DEFAULT_WORKSPACE
_workspace_lock = threading.Lock()

# Temp staging directory — files wait here until user confirms save
TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'temp'))
os.makedirs(TEMP_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000"])
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ─── System Prompts ───────────────────────────────────────────────────────────

ORCHESTRATOR_PROMPT = """
คุณคือ AI Orchestrator ของระบบ Internal AI Assistant ภายในบริษัท
หน้าที่ของคุณคือวิเคราะห์งานที่ได้รับและตัดสินใจว่าควรส่งให้ Agent ไหน

ตอบกลับด้วย JSON เท่านั้น ห้ามมีข้อความอื่น:
{"agent": "hr", "reason": "เหตุผลสั้นๆ"}
หรือ
{"agent": "accounting", "reason": "เหตุผลสั้นๆ"}
หรือ
{"agent": "manager", "reason": "เหตุผลสั้นๆ"}
หรือ
{"agent": "pm", "reason": "เหตุผลสั้นๆ"}

HR Agent เหมาะกับ:
- งานเกี่ยวกับพนักงาน สัญญาจ้าง การเลิกจ้าง
- Job Description และการสรรหาบุคลากร
- นโยบายบริษัท กฎระเบียบ สวัสดิการ
- อีเมลแจ้งพนักงาน การลา การประเมิน

Accounting Agent เหมาะกับ:
- Invoice ใบเสร็จ ใบแจ้งหนี้
- งบประมาณ รายรับรายจ่าย
- รายงานการเงิน การวิเคราะห์ตัวเลข
- ค่าใช้จ่าย การเบิกจ่าย

Manager Advisor เหมาะกับ:
- การให้ Feedback และการจัดการผลการทำงานของทีม
- การจัดสรรงบประมาณและทรัพยากรของทีม
- การตัดสินใจจัดลำดับความสำคัญของงาน
- ความขัดแย้งในทีม ขวัญกำลังใจ
- การขอเพิ่มอัตรากำลังคน (Headcount Request)

PM Agent เหมาะกับ:
- งานที่ครอบคลุมหลาย domain พร้อมกัน เช่น ต้องทำทั้งสัญญาจ้าง (HR) และ Invoice (Accounting)
- Request ที่ต้องการเอกสารหลายประเภทในคราวเดียว
- งาน onboarding พนักงานใหม่ที่ต้องการทั้งเอกสาร HR และการเงิน
"""

PM_PROMPT = """OUTPUT FORMAT — CRITICAL:
ตอบกลับด้วย JSON เท่านั้น ห้ามมีข้อความอื่นนอกจาก JSON ด้านล่าง
ห้ามมี markdown code fences ห้ามมีคำอธิบาย ห้ามมี prose ใดๆ ทั้งสิ้น

{"subtasks": [{"agent": "hr", "task": "รายละเอียด task"}, {"agent": "accounting", "task": "รายละเอียด task"}]}

คุณคือ PM Agent (Project Manager) ของระบบ AI Assistant
หน้าที่ของคุณคือวิเคราะห์งานที่ได้รับและแบ่งออกเป็น subtasks พร้อมกำหนดว่าแต่ละ subtask ควรใช้ Agent ไหน

กฎสำคัญ:
1. แต่ละ task ต้องเป็น self-contained — คัดลอกข้อมูลสำคัญจาก request มาใส่โดยตรง (ชื่อ, ตัวเลข, วันที่, เงื่อนไข) ห้ามอ้างอิงว่า "ดูจากบริบทด้านบน"
2. Agent ที่ใช้ได้: "hr", "accounting", "manager" เท่านั้น — ห้ามใส่ "pm"
3. กำหนดให้แต่ละ Agent บันทึกผลลัพธ์เป็นไฟล์ด้วย เช่น "...และบันทึกผลลัพธ์เป็นไฟล์ชื่อ contract_somchai.md ใน workspace"
4. ใช้ Agent เดียวเมื่องานนั้นเป็นของ domain เดียวชัดเจน ใช้หลาย Agent เฉพาะเมื่อ request ครอบคลุมหลายด้านจริงๆ

HR Agent: สัญญาจ้าง, JD, นโยบาย HR, อีเมลพนักงาน, การลา, การเลิกจ้าง
Accounting Agent: Invoice, ใบเสร็จ, รายงานการเงิน, งบประมาณ, ค่าใช้จ่าย
Manager Advisor: คำแนะนำการบริหารทีม, Feedback, ขวัญกำลังใจ, Headcount Request

ย้ำอีกครั้ง: ตอบกลับด้วย JSON เท่านั้น ไม่มีข้อความอื่น ไม่มี code fence ไม่มีคำนำ ไม่มีคำลงท้าย
"""

HR_PROMPT = """
คุณคือ HR Agent ผู้เชี่ยวชาญด้านทรัพยากรมนุษย์ของบริษัทไทย
สร้างเอกสาร HR ที่ถูกต้อง เป็นมืออาชีพ และเหมาะสมกับบริบทของบริษัทไทย

แนวทางการทำงาน:
- ใช้ภาษาไทยที่เป็นทางการและสุภาพ
- ระบุวันที่เป็น พ.ศ.
- ใส่ช่องว่างให้กรอกข้อมูลที่ยังไม่ทราบ เช่น [วันที่] [ลายมือชื่อ]
- ครอบคลุมประเด็นสำคัญตามกฎหมายแรงงานไทย

สำคัญ: ระบุที่ท้ายเอกสารทุกครั้งว่า
"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"

หลังแสดงเอกสารแล้ว ให้ลงท้ายด้วยบรรทัดนี้เสมอ:
"💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์"
"""

ACCOUNTING_PROMPT = """
คุณคือ Accounting Agent ผู้เชี่ยวชาญด้านบัญชีและการเงินของบริษัทไทย
สร้างเอกสารการเงินที่ถูกต้อง เป็นมืออาชีพ และเหมาะสมกับระบบบัญชีไทย

ข้อมูลปัจจุบัน:
- ปัจจุบันคือ พ.ศ. 2569 (ค.ศ. 2026)
- ใช้วันที่ปัจจุบันเป็นค่าเริ่มต้นในเอกสาร เว้นแต่จะระบุเป็นอย่างอื่น

แนวทางการทำงาน:
- ใช้ภาษาไทยที่เป็นทางการ
- ใช้รูปแบบตัวเลขที่ถูกต้อง เช่น 35,000.00 บาท
- ระบุวันที่เป็น พ.ศ. (ตัวอย่าง: 23 มีนาคม พ.ศ. 2569)
- ใส่เลขที่เอกสาร [XXX-YYYY-NNNN] เผื่อให้แก้ไข
- ระบุเงื่อนไขการชำระเงินให้ชัดเจน

กฎสำหรับ VAT 7%:
- ใช้ VAT เฉพาะกับ Invoice / ใบกำกับภาษี / ใบแจ้งหนี้เท่านั้น
- ห้ามใช้ VAT กับรายงานค่าใช้จ่ายภายใน (Expense Report) หรือเอกสารงบประมาณ
- สำหรับ Invoice ให้คำนวณ: ยอดก่อน VAT + VAT 7% = ยอดรวมทั้งสิ้น

กฎสำหรับข้อมูลภาษี (ใช้กับ Invoice/ใบกำกับภาษีเท่านั้น):
- ใส่ placeholder เลขประจำตัวผู้เสียภาษี 13 หลัก ทั้งฝ่ายผู้ออกและผู้รับ
  ตัวอย่าง: เลขประจำตัวผู้เสียภาษี: [X-XXXX-XXXXX-XX-X]
- ใส่ข้อมูลสาขา ตัวอย่าง: สาขา: [สำนักงานใหญ่] หรือ [สาขาที่ XXXXX]
- ระบุที่อยู่เต็มของทั้งสองฝ่าย

สำคัญ: ระบุที่ท้ายเอกสารทุกครั้งว่า
"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"

หลังแสดงเอกสารแล้ว ให้ลงท้ายด้วยบรรทัดนี้เสมอ:
"💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์"
"""

MANAGER_PROMPT = """
คุณคือ Manager Advisor ผู้เชี่ยวชาญด้านการบริหารทีมสำหรับ Team Lead และผู้จัดการในองค์กรไทย
ให้คำแนะนำที่นำไปปฏิบัติได้จริงภายใน 48 ชั่วโมง

ความเชี่ยวชาญ:
- การให้ Feedback และการประเมินผลการทำงาน
- การจัดสรรงบประมาณและทรัพยากรของทีม
- การตัดสินใจจัดลำดับความสำคัญของงาน
- การจัดการสถานการณ์คนในทีม เช่น ความขัดแย้ง ขวัญกำลังใจ
- การขอเพิ่มอัตรากำลังคน (Headcount Request)

แนวทางการตอบ:
- ระบุขั้นตอนที่ทำได้ทันทีอย่างชัดเจน
- เมื่อแนะนำการให้ Feedback ให้เขียน Script คำพูดจริงที่ผู้จัดการสามารถนำไปพูดได้เลย
- คำนึงถึงบริบทวัฒนธรรมการทำงานแบบไทย
- ใช้ภาษาที่กระชับ ตรงประเด็น ไม่อ้อมค้อม

สำคัญ: ระบุที่ท้ายเอกสารทุกครั้งว่า
"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"

หลังแสดงเอกสารแล้ว ให้ลงท้ายด้วยบรรทัดนี้เสมอ:
"💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์"
"""

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
    }
]

# ─── MCP Tool Executor ────────────────────────────────────────────────────────


def _execute_tool(workspace: str, tool_name: str, tool_args: dict) -> str:
    """Execute a named MCP filesystem tool and return result string."""
    try:
        if tool_name == 'create_file':
            return fs_create_file(workspace, tool_args['filename'], tool_args['content'])
        elif tool_name == 'read_file':
            return fs_read_file(workspace, tool_args['filename'])
        elif tool_name == 'update_file':
            return fs_update_file(workspace, tool_args['filename'], tool_args['content'])
        elif tool_name == 'delete_file':
            return fs_delete_file(workspace, tool_args['filename'])
        elif tool_name == 'list_files':
            files = fs_list_files(workspace)
            if not files:
                return "workspace ว่างเปล่า ยังไม่มีไฟล์"
            return "\n".join(
                f"- {f['name']} ({f['size']} bytes, แก้ไขล่าสุด: {f['modified']})"
                for f in files
            )
        else:
            return f"❌ ไม่รู้จัก tool: {tool_name}"
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return f"❌ เกิดข้อผิดพลาด: {str(e)}"


# ─── Agentic Tool-Calling Loop ────────────────────────────────────────────────


def run_agent_with_tools(system_prompt: str, user_message: str, workspace: str,
                         agent_label: str, max_tokens: int = 8000, max_iterations: int = 5):
    """Agentic loop with true streaming:
    - Text chunks stream to user as they arrive (delta.content)
    - Tool calls accumulate silently in background (delta.tool_calls)
    - After stream ends: execute tools if any, then continue loop if needed
    Generator that yields SSE data strings."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    for iteration in range(max_iterations):
        text_streamed = ""
        tool_calls_acc = {}   # index → {"id", "name", "arguments"}

        try:
            stream = client.chat.completions.create(
                model=MODEL,
                max_tokens=max_tokens,
                messages=messages,
                tools=MCP_TOOLS,
                tool_choice="auto",
                stream=True
            )
        except RateLimitError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'API ถูกใช้งานเกิน limit กรุณารอสักครู่แล้วลองใหม่'})}\n\n"
            return
        except APITimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'API ใช้เวลานานเกินไป กรุณาลองใหม่'})}\n\n"
            return
        except APIError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'เกิดข้อผิดพลาดจาก API: {str(e)}'})}\n\n"
            return

        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # Stream text to user immediately
                if delta and delta.content:
                    text_streamed += delta.content
                    yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"

                # Accumulate tool_calls silently
                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.id:
                            tool_calls_acc[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_acc[idx]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments
        except Exception as stream_err:
            logger.error(f"[{agent_label}] Streaming error: {stream_err}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดระหว่าง streaming กรุณาลองใหม่'})}\n\n"
            return

        # No tool calls → text was streamed, done
        if not tool_calls_acc:
            return

        # Build tool_calls list for messages history
        tool_calls_list = [
            {
                "id": tool_calls_acc[i]["id"],
                "type": "function",
                "function": {
                    "name": tool_calls_acc[i]["name"],
                    "arguments": tool_calls_acc[i]["arguments"]
                }
            }
            for i in sorted(tool_calls_acc.keys())
        ]

        messages.append({
            "role": "assistant",
            "content": text_streamed or None,
            "tool_calls": tool_calls_list
        })

        # Execute each tool
        for tc in tool_calls_list:
            tool_name = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                logger.error(f"[{agent_label}] Invalid tool args for {tool_name}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'{agent_label} ส่ง tool arguments ผิดรูปแบบ'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'message': f'{agent_label} กำลังบันทึก: {tool_name}...'})}\n\n"
            logger.info(f"[{agent_label}] tool_call: {tool_name}({list(tool_args.keys())})")

            result = _execute_tool(workspace, tool_name, tool_args)
            logger.info(f"[{agent_label}] tool_result: {result[:80]}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result
            })

            yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'result': result[:200]})}\n\n"

        # If text was already streamed before tools → done (no need for another LLM call)
        if text_streamed:
            return
        # Otherwise continue loop so LLM can generate response text after tool results

    yield f"data: {json.dumps({'type': 'error', 'message': f'{agent_label} ทำงานเกินจำนวนรอบที่กำหนด กรุณาลองใหม่'})}\n\n"


# ─── Confirmation Flow Helpers ───────────────────────────────────────────────

_SAVE_KEYWORDS = {
    'บันทึก', 'save', 'เซฟ', 'ยืนยัน', 'ตกลง', 'ได้เลย', 'ok', 'โอเค',
    'บันทึกได้', 'บันทึกเลย', 'บันทึกได้เลย', 'ใช่', 'ใช้ได้'
}


def _is_save_intent(message: str) -> bool:
    """Return True if user message signals intent to save the document."""
    msg = message.lower().strip()
    return any(kw in msg for kw in _SAVE_KEYWORDS)


def _suggest_filename(agent: str, content: str) -> str:
    """Generate a meaningful filename from agent type and document content."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    m = re.search(r'#\s*(.{3,30})', content)
    if m:
        slug = re.sub(r'[^\w]', '_', m.group(1).strip())
        slug = re.sub(r'_+', '_', slug)[:22].strip('_')
        if len(slug) >= 3:
            return f"{agent}_{slug}_{ts}.md"
    return f"{agent}_{ts}.md"


def _write_temp(content: str, agent: str) -> str:
    """Write document content to temp staging dir. Returns absolute temp file path."""
    filename = _suggest_filename(agent, content)
    temp_path = os.path.join(TEMP_DIR, filename)
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"Staged to temp: {filename}")
    return temp_path


def _move_to_workspace(temp_path: str, workspace: str) -> str:
    """Move staged file from temp to workspace. Returns filename.
    Uses os.replace (atomic) on same drive, falls back to shutil.move for cross-drive."""
    import shutil
    filename = os.path.basename(temp_path)
    dest = os.path.join(workspace, filename)
    try:
        os.replace(temp_path, dest)  # Atomic on same drive
    except OSError:
        shutil.move(temp_path, dest)  # Fallback: cross-drive (copy + delete)
    logger.info(f"Moved to workspace: {filename}")
    return filename


def _cleanup_old_temp():
    """Remove temp files older than 1 hour to prevent accumulation."""
    cutoff = datetime.now().timestamp() - 3600
    try:
        for fname in os.listdir(TEMP_DIR):
            fpath = os.path.join(TEMP_DIR, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                logger.info(f"Cleaned old temp file: {fname}")
    except Exception as e:
        logger.warning(f"Temp cleanup error: {e}")


def stream_agent(system_prompt: str, message: str, agent_label: str, max_tokens: int = 8000):
    """Stream agent response without MCP tools — for initial document generation.
    Generator that yields SSE data strings."""
    try:
        stream = client.chat.completions.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            stream=True
        )
    except RateLimitError:
        yield f"data: {json.dumps({'type': 'error', 'message': 'API ถูกใช้งานเกิน limit กรุณารอสักครู่แล้วลองใหม่'})}\n\n"
        return
    except APITimeoutError:
        yield f"data: {json.dumps({'type': 'error', 'message': 'API ใช้เวลานานเกินไป กรุณาลองใหม่'})}\n\n"
        return
    except APIError as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'เกิดข้อผิดพลาดจาก API: {str(e)}'})}\n\n"
        return
    try:
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield f"data: {json.dumps({'type': 'text', 'content': chunk.choices[0].delta.content})}\n\n"
    except Exception as e:
        logger.error(f"[{agent_label}] Streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดระหว่าง streaming กรุณาลองใหม่'})}\n\n"


def handle_save(pending_doc: str, pending_agent: str, workspace: str):
    """Save the pending document to workspace without another LLM call.
    Generator that yields SSE data strings."""
    try:
        filename = _suggest_filename(pending_agent, pending_doc)
        yield f"data: {json.dumps({'type': 'status', 'message': f'กำลังบันทึกไฟล์ {filename}...'})}\n\n"
        result = _execute_tool(workspace, 'create_file', {
            'filename': filename,
            'content': pending_doc
        })
        yield f"data: {json.dumps({'type': 'text', 'content': f'✅ {result}'})}\n\n"
        yield f"data: {json.dumps({'type': 'tool_result', 'tool': 'create_file', 'result': result})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'ไม่สามารถบันทึกไฟล์ได้: {str(e)}'})}\n\n"


def handle_revise(pending_doc: str, pending_agent: str, instruction: str, workspace: str):
    """Revise the pending document based on user instruction.
    Generator that yields SSE data strings."""
    if pending_agent == 'hr':
        system_prompt = HR_PROMPT
        agent_label = 'HR Agent'
        max_tokens = 7500
    elif pending_agent == 'manager':
        system_prompt = MANAGER_PROMPT
        agent_label = 'Manager Advisor'
        max_tokens = 8000
    else:
        system_prompt = ACCOUNTING_PROMPT
        agent_label = 'Accounting Agent'
        max_tokens = 6000

    yield f"data: {json.dumps({'type': 'agent', 'agent': pending_agent, 'reason': 'แก้ไขเอกสาร'})}\n\n"
    yield f"data: {json.dumps({'type': 'status', 'message': f'{agent_label} กำลังแก้ไขเอกสาร...'})}\n\n"

    revise_message = (
        f"แก้ไขเอกสารต่อไปนี้ตามคำสั่งที่ได้รับ\n\n"
        f"คำสั่งแก้ไข: {instruction}\n\n"
        f"เอกสารเดิม:\n{pending_doc}"
    )
    for sse in stream_agent(system_prompt, revise_message, agent_label, max_tokens):
        yield sse


def _is_safe_temp_path(path: str) -> bool:
    """Validate that a path is inside TEMP_DIR to prevent path traversal attacks."""
    try:
        resolved = os.path.realpath(os.path.abspath(path))
        return os.path.commonpath([resolved, TEMP_DIR]) == TEMP_DIR
    except Exception:
        return False


def handle_pm_save(temp_paths: list, workspace: str):
    """Move all PM staged temp files to workspace. Generator that yields SSE data strings."""
    saved = []
    for temp_path in temp_paths:
        # Security: reject paths outside TEMP_DIR
        if not _is_safe_temp_path(temp_path):
            logger.warning(f"Rejected unsafe temp path: {temp_path}")
            continue
        if not os.path.isfile(temp_path):
            logger.warning(f"Temp file not found (expired?): {temp_path}")
            continue
        try:
            filename = _move_to_workspace(temp_path, workspace)
            saved.append(filename)
            yield f"data: {json.dumps({'type': 'tool_result', 'tool': 'create_file', 'result': f'บันทึก {filename} เรียบร้อย'})}\n\n"
        except Exception as e:
            logger.error(f"Failed to move temp file {temp_path}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'ไม่สามารถบันทึก {os.path.basename(temp_path)}: {str(e)}'})}\n\n"

    count = len(saved)
    if count > 0:
        names = ', '.join(saved)
        yield f"data: {json.dumps({'type': 'text', 'content': f'✅ บันทึก {count} ไฟล์เรียบร้อย\\n{names}'})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'text', 'content': 'ไม่พบไฟล์ที่รอบันทึก (อาจหมดอายุแล้ว) กรุณาสร้างเอกสารใหม่'})}\n\n"


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_file('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    if not request.json:
        return jsonify({'error': 'Invalid request'}), 400
    user_input = request.json.get('message', '').strip()
    if not user_input:
        return jsonify({'error': 'ไม่มีข้อความ'}), 400
    if len(user_input) > 5000:
        return jsonify({'error': 'ข้อความยาวเกินไป (สูงสุด 5,000 ตัวอักษร)'}), 400

    # Confirmation flow fields
    pending_doc        = request.json.get('pending_doc', '').strip()
    pending_agent      = request.json.get('pending_agent', '').strip()
    pending_temp_paths = request.json.get('pending_temp_paths', [])
    if not isinstance(pending_temp_paths, list):
        pending_temp_paths = []

    def generate():
        with _workspace_lock:
            workspace = WORKSPACE_PATH
        os.makedirs(workspace, exist_ok=True)
        _cleanup_old_temp()

        # ── Follow-up: PM staged files waiting for confirmation ──────────────
        if pending_temp_paths:
            if _is_save_intent(user_input):
                for sse in handle_pm_save(pending_temp_paths, workspace):
                    yield sse
            else:
                # Discard temp files (user cancelled or gave unexpected input)
                for tp in pending_temp_paths:
                    if _is_safe_temp_path(tp) and os.path.isfile(tp):
                        os.remove(tp)
                        logger.info(f"Discarded temp file: {os.path.basename(tp)}")
                yield f"data: {json.dumps({'type': 'text', 'content': 'ยกเลิกการบันทึกไฟล์เรียบร้อย'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # ── Follow-up: single-agent doc confirming/editing ───────────────────
        if pending_doc and pending_agent:
            if _is_save_intent(user_input):
                for sse in handle_save(pending_doc, pending_agent, workspace):
                    yield sse
            else:
                for sse in handle_revise(pending_doc, pending_agent, user_input, workspace):
                    yield sse
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        try:
            # Step 1: Orchestrator เลือก Agent
            yield f"data: {json.dumps({'type': 'status', 'message': 'กำลังวิเคราะห์งาน...'})}\n\n"

            try:
                orchestrator_response = client.chat.completions.create(
                    model=MODEL,
                    max_tokens=1024,
                    messages=[
                        {"role": "system", "content": ORCHESTRATOR_PROMPT},
                        {"role": "user", "content": user_input}
                    ]
                )
            except RateLimitError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'API ถูกใช้งานเกิน limit กรุณารอสักครู่แล้วลองใหม่'})}\n\n"
                return
            except APITimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'API ใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง'})}\n\n"
                return
            except APIError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดจาก API กรุณาลองใหม่'})}\n\n"
                return

            raw = orchestrator_response.choices[0].message.content
            if not raw:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ไม่ตอบกลับ กรุณาลองใหม่'})}\n\n"
                return
            try:
                raw = _extract_json(raw)
                routing = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
                return
            agent = routing.get('agent', 'hr')
            reason = routing.get('reason', '')

            yield f"data: {json.dumps({'type': 'agent', 'agent': agent, 'reason': reason})}\n\n"

            # Step 2: Route to agent(s)
            if agent == 'pm':
                # PM path: decompose → multiple agents
                yield f"data: {json.dumps({'type': 'status', 'message': 'PM Agent กำลังวางแผนงาน...'})}\n\n"

                try:
                    pm_response = client.chat.completions.create(
                        model=MODEL,
                        max_tokens=1024,
                        messages=[
                            {"role": "system", "content": PM_PROMPT},
                            {"role": "user", "content": user_input}
                        ]
                    )
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'PM Agent เกิดข้อผิดพลาด: {str(e)}'})}\n\n"
                    return

                raw_pm = pm_response.choices[0].message.content or ''
                try:
                    raw_pm = _extract_json(raw_pm)
                    pm_data = json.loads(raw_pm)
                    subtasks = pm_data.get('subtasks', [])
                except (json.JSONDecodeError, ValueError):
                    logger.warning(f"PM Agent bad response: {raw_pm[:300]!r}")
                    yield f"data: {json.dumps({'type': 'error', 'message': 'PM Agent ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
                    return

                # Filter out invalid agents (e.g. 'pm' self-reference)
                valid_agents = {'hr', 'accounting', 'manager'}
                subtasks = [s for s in subtasks if s.get('agent') in valid_agents]

                if not subtasks:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'PM Agent ไม่สามารถแบ่งงานได้ กรุณาลองใหม่'})}\n\n"
                    return

                yield f"data: {json.dumps({'type': 'pm_plan', 'subtasks': subtasks})}\n\n"
                logger.info(f"PM Agent decomposed into {len(subtasks)} subtasks")

                for i, subtask in enumerate(subtasks):
                    sub_agent = subtask.get('agent', 'hr')
                    sub_task = subtask.get('task', user_input)

                    if sub_agent == 'hr':
                        sub_prompt = HR_PROMPT
                        sub_label = 'HR Agent'
                        sub_max_tokens = 7500
                    elif sub_agent == 'manager':
                        sub_prompt = MANAGER_PROMPT
                        sub_label = 'Manager Advisor'
                        sub_max_tokens = 8000
                    else:
                        sub_prompt = ACCOUNTING_PROMPT
                        sub_label = 'Accounting Agent'
                        sub_max_tokens = 6000

                    yield f"data: {json.dumps({'type': 'agent', 'agent': sub_agent, 'reason': f'Subtask {i+1}/{len(subtasks)}'})}\n\n"
                    yield f"data: {json.dumps({'type': 'status', 'message': f'{sub_label} กำลังสร้างเอกสาร...'})}\n\n"
                    logger.info(f"PM → {sub_label}: {sub_task[:60]}")

                    # Stream content to frontend AND capture it for temp staging
                    subtask_chunks = []
                    for sse_line in stream_agent(sub_prompt, sub_task, sub_label, sub_max_tokens):
                        yield sse_line
                        if sse_line.startswith('data: '):
                            try:
                                d = json.loads(sse_line[6:])
                                if d.get('type') == 'text':
                                    subtask_chunks.append(d.get('content', ''))
                            except Exception:
                                pass

                    # Write captured content to temp staging (hidden from workspace/file panel)
                    full_content = ''.join(subtask_chunks)
                    if full_content.strip():
                        temp_path = _write_temp(full_content, sub_agent)
                        filename = os.path.basename(temp_path)
                        yield f"data: {json.dumps({'type': 'pending_file', 'temp_path': temp_path, 'filename': filename, 'agent': sub_agent})}\n\n"

                    yield f"data: {json.dumps({'type': 'subtask_done', 'agent': sub_agent, 'index': i, 'total': len(subtasks)})}\n\n"

            else:
                # Single-agent path — stream only, no auto-save (user confirms later)
                if agent == 'hr':
                    system_prompt = HR_PROMPT
                    agent_label = 'HR Agent'
                    agent_max_tokens = 7500
                elif agent == 'manager':
                    system_prompt = MANAGER_PROMPT
                    agent_label = 'Manager Advisor'
                    agent_max_tokens = 8000
                else:
                    system_prompt = ACCOUNTING_PROMPT
                    agent_label = 'Accounting Agent'
                    agent_max_tokens = 6000

                logger.info(f"Routed to {agent_label}: {user_input[:60]}")
                yield f"data: {json.dumps({'type': 'status', 'message': f'{agent_label} กำลังสร้างเอกสาร...'})}\n\n"

                for sse_line in stream_agent(system_prompt, user_input, agent_label, agent_max_tokens):
                    yield sse_line

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except json.JSONDecodeError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดจากระบบ กรุณาลองใหม่อีกครั้ง'})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/api/workspace', methods=['GET'])
def get_workspace():
    with _workspace_lock:
        wp = WORKSPACE_PATH
    return jsonify({
        'path': wp,
        'exists': os.path.isdir(wp),
        'files': len(fs_list_files(wp))
    })


@app.route('/api/workspace', methods=['POST'])
def set_workspace():
    global WORKSPACE_PATH
    data = request.json or {}
    new_path = data.get('path', '').strip()
    if not new_path:
        return jsonify({'error': 'ระบุ path ไม่ถูกต้อง'}), 400
    abs_path = os.path.abspath(new_path)
    # Basic safety: reject suspiciously short paths (e.g. bare drive root "C:\")
    if len(abs_path) <= 3:
        return jsonify({'error': 'Path ไม่ปลอดภัย กรุณาระบุ directory ที่ชัดเจนกว่านี้'}), 400
    try:
        os.makedirs(abs_path, exist_ok=True)
    except OSError as e:
        return jsonify({'error': f'ไม่สามารถสร้าง directory ได้: {str(e)}'}), 400
    with _workspace_lock:
        WORKSPACE_PATH = abs_path
    logger.info(f"Workspace changed to: {abs_path}")
    return jsonify({'path': abs_path, 'exists': True})


@app.route('/api/files')
def list_files_snapshot():
    with _workspace_lock:
        wp = WORKSPACE_PATH
    return jsonify({'workspace': wp, 'files': fs_list_files(wp)})


@app.route('/api/files/stream')
def files_stream():
    def generate():
        with _workspace_lock:
            wp = WORKSPACE_PATH
        os.makedirs(wp, exist_ok=True)

        event_queue = queue.Queue(maxsize=20)

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                if not event.is_directory:
                    try:
                        event_queue.put_nowait('changed')
                    except queue.Full:
                        pass

        observer = Observer()
        observer.schedule(Handler(), wp, recursive=False)
        observer.start()

        try:
            # Send initial snapshot
            files = fs_list_files(wp)
            yield f"data: {json.dumps({'type': 'files', 'files': files, 'workspace': wp})}\n\n"

            while True:
                try:
                    event_queue.get(timeout=25)
                    # Drain stacked events
                    while not event_queue.empty():
                        try:
                            event_queue.get_nowait()
                        except queue.Empty:
                            break
                except queue.Empty:
                    # Heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    continue

                files = fs_list_files(wp)
                yield f"data: {json.dumps({'type': 'files', 'files': files, 'workspace': wp})}\n\n"

        except GeneratorExit:
            pass
        finally:
            observer.stop()
            observer.join(timeout=2)

    return Response(
        generate(),
        mimetype='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/api/health')
def health():
    with _workspace_lock:
        wp = WORKSPACE_PATH
    return jsonify({
        'status': 'ok',
        'model': MODEL,
        'provider': 'openrouter',
        'api_key_configured': bool(OPENROUTER_API_KEY),
        'workspace': wp,
        'workspace_exists': os.path.isdir(wp)
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
