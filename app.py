from flask import Flask, request, jsonify, Response, send_file
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

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress WeasyPrint's extremely verbose font subsetting logs
logging.getLogger('fontTools').setLevel(logging.ERROR)
logging.getLogger('weasyprint').setLevel(logging.WARNING)


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
_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# Allowed workspace roots — comma-separated absolute paths from env
# Fallback: project root only (same behaviour as before)
_ALLOWED_ROOTS = [
    os.path.realpath(p.strip())
    for p in os.getenv("ALLOWED_WORKSPACE_ROOTS", _PROJECT_ROOT).split(",")
    if p.strip()
] or [_PROJECT_ROOT]

# Workspace state — mutable at runtime via /api/workspace
_DEFAULT_WORKSPACE = os.path.abspath(
    os.getenv("WORKSPACE_PATH", os.path.join(_PROJECT_ROOT, "workspace"))
)
WORKSPACE_PATH = _DEFAULT_WORKSPACE
_workspace_lock = threading.Lock()

# Global event bus: notify sidebar SSE clients when a file is saved by any agent.
# Keyed by workspace path; each value is a list of queue.Queue objects (one per SSE client).
# This ensures the sidebar refreshes immediately even when watchdog misses events
# (e.g., after the watched directory was deleted and recreated).
_ws_change_queues: dict = {}
_ws_change_lock = threading.Lock()


def _notify_workspace_changed(wp: str) -> None:
    """Push a 'changed' event to all sidebar SSE clients watching `wp`."""
    with _ws_change_lock:
        queues = list(_ws_change_queues.get(wp, []))
    for q in queues:
        try:
            q.put_nowait('changed')
        except queue.Full:
            pass


# Temp staging directory — files wait here until user confirms save
TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'temp'))
os.makedirs(TEMP_DIR, exist_ok=True)

app = Flask(__name__)
app.json.ensure_ascii = False  # Return Thai text as-is in JSON responses
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000",
                   "http://0.0.0.0:5000"])
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
db.init_db()

# ─── System Prompts ───────────────────────────────────────────────────────────

def _normalize_workspace_path(path: str) -> str:
    """Normalize a workspace path relative to the current process."""
    return os.path.abspath(path or _DEFAULT_WORKSPACE)


def _is_allowed_workspace_path(path: str) -> bool:
    """Allow runtime workspace changes only under configured allowed roots."""
    try:
        real = os.path.realpath(path)
        return any(
            os.path.commonpath([root, real]) == root and real != root
            for root in _ALLOWED_ROOTS
        )
    except ValueError:
        return False


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

การใช้ list_files และ read_file:
- ใช้เฉพาะเมื่อผู้ใช้ขอแก้ไขหรือต่อยอดเอกสารที่มีอยู่แล้วโดยตรง เช่น "แก้ไขสัญญา X", "อัพเดทไฟล์ Y"
- ใช้เฉพาะเมื่อผู้ใช้ระบุชื่อไฟล์ชัดเจนในคำขอ
- ถ้าผู้ใช้ขอสร้างเอกสารใหม่ หรือไม่ได้อ้างถึงไฟล์ที่มีอยู่ ให้สร้างจากข้อมูลในคำขอทันที อย่าเรียก list_files หรือ read_file
- อย่าอ่านไฟล์ที่ดู "น่าจะเกี่ยวข้อง" แต่ผู้ใช้ไม่ได้อ้างถึง — ทำให้เกิดการสร้างเอกสารผิดบริบท

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

การใช้ list_files และ read_file:
- ใช้เฉพาะเมื่อผู้ใช้ขอแก้ไขหรือต่อยอดเอกสารที่มีอยู่แล้วโดยตรง เช่น "แก้ไข invoice X", "อัพเดทไฟล์ Y"
- ใช้เฉพาะเมื่อผู้ใช้ระบุชื่อไฟล์ชัดเจนในคำขอ
- ถ้าผู้ใช้ขอสร้างเอกสารใหม่ หรือไม่ได้อ้างถึงไฟล์ที่มีอยู่ ให้สร้างจากข้อมูลในคำขอทันที อย่าเรียก list_files หรือ read_file
- อย่าอ่านไฟล์ที่ดู "น่าจะเกี่ยวข้อง" แต่ผู้ใช้ไม่ได้อ้างถึง — ทำให้เกิดการสร้างเอกสารผิดบริบท

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

การใช้ list_files และ read_file:
- ใช้เฉพาะเมื่อผู้ใช้ขอแก้ไขหรืออ้างอิงเอกสารที่มีอยู่แล้วโดยตรง เช่น "ดูแผนงานที่บันทึกไว้", "แก้ไขไฟล์ X"
- ใช้เฉพาะเมื่อผู้ใช้ระบุชื่อไฟล์ชัดเจนในคำขอ
- ถ้าผู้ใช้ขอคำแนะนำหรือสร้างเอกสารใหม่ ให้ตอบจากข้อมูลในคำขอทันที อย่าเรียก list_files หรือ read_file
- อย่าอ่านไฟล์ที่ดู "น่าจะเกี่ยวข้อง" แต่ผู้ใช้ไม่ได้อ้างถึง — ทำให้เกิดการตอบผิดบริบท

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

# Read-only subset — given to HR/Accounting/Manager so they can understand the
# workspace before writing, but cannot write/delete files directly.
READ_ONLY_TOOLS = [t for t in MCP_TOOLS if t['function']['name'] in ('list_files', 'read_file')]

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


def _tool_result_is_error(result: str) -> bool:
    """Return True when a tool result string represents a failure."""
    return result.strip().startswith('❌')


# ─── Agentic Tool-Calling Loop ────────────────────────────────────────────────


def run_agent_with_tools(system_prompt: str, user_message: str, workspace: str,
                         agent_label: str, max_tokens: int = 8000, max_iterations: int = 5,
                         tools: list = None):
    """Agentic loop with true streaming:
    - Text chunks stream to user as they arrive (delta.content)
    - Tool calls accumulate silently in background (delta.tool_calls)
    - After stream ends: execute tools if any, then continue loop if needed
    - tools: defaults to MCP_TOOLS (all); pass READ_ONLY_TOOLS to restrict to read-only
    Generator that yields SSE data strings."""
    if tools is None:
        tools = MCP_TOOLS
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
                tools=tools,
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
        _allowed_tool_names = {t['function']['name'] for t in tools}
        _read_tool_names = {'list_files', 'read_file'}
        for tc in tool_calls_list:
            tool_name = tc["function"]["name"]

            # Enforce allow-list — blocks prompt-injected calls to tools not in scope
            if tool_name not in _allowed_tool_names:
                logger.warning(f"[{agent_label}] Blocked disallowed tool call: {tool_name}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'{agent_label} พยายามใช้ tool ที่ไม่ได้รับอนุญาต'})}\n\n"
                return

            try:
                tool_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                logger.error(f"[{agent_label}] Invalid tool args for {tool_name}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'{agent_label} ส่ง tool arguments ผิดรูปแบบ'})}\n\n"
                return

            _status_msg = f'{agent_label} กำลังอ่านข้อมูล...' if tool_name in _read_tool_names else f'{agent_label} กำลังบันทึก: {tool_name}...'
            yield f"data: {json.dumps({'type': 'status', 'message': _status_msg})}\n\n"
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
    'บันทึกได้', 'บันทึกเลย', 'บันทึกได้เลย', 'ใช้ได้'
    # นำ 'ใช่' ออก — เป็น substring ของ 'ไม่ใช่', 'ใช่ไหม' ฯลฯ ทำให้ false positive สูง
}

_SAVE_NEGATIVE_PREFIX = {'ไม่ใช่', 'ไม่ใช้'}

_DISCARD_KEYWORDS = {
    'ยกเลิก', 'cancel', 'ไม่เอา', 'ไม่บันทึก', 'ไม่ต้องการ',
    'ข้ามไป', 'ลบทิ้ง', 'discard'
    # นำ 'งานใหม่' และ 'เริ่มใหม่' ออก — เป็นวลีที่ใช้ในงานจริง ไม่ใช่ cancel signal
}

_EDIT_KEYWORDS = {
    'แก้ไข', 'แก้', 'ปรับ', 'ปรับปรุง', 'ปรับแก้', 'เพิ่ม', 'ลบ',
    'เปลี่ยน', 'แทนที่', 'เพิ่มเติม', 'ตัดออก', 'แก้ตรง', 'ปรับตรง',
    'edit', 'modify', 'update', 'change', 'fix', 'adjust', 'add', 'remove',
    'delete', 'replace', 'revise'
}


def _is_save_intent(message: str) -> bool:
    """Return True if user message signals intent to save the document."""
    msg = message.lower().strip()
    if any(neg in msg for neg in _SAVE_NEGATIVE_PREFIX):
        return False
    return any(kw in msg for kw in _SAVE_KEYWORDS)


def _is_discard_intent(message: str) -> bool:
    """Return True if user message signals intent to discard the pending document."""
    msg = message.lower().strip()
    return any(kw in msg for kw in _DISCARD_KEYWORDS)


def _is_pure_discard(message: str) -> bool:
    """Return True if message is ONLY a discard keyword — no additional task content."""
    msg = message.lower().strip()
    return msg in _DISCARD_KEYWORDS


def _is_edit_intent(message: str) -> bool:
    """Return True if user message is an edit instruction for the current pending doc."""
    msg = message.lower().strip()
    return any(kw in msg for kw in _EDIT_KEYWORDS)


def _suggest_filename(agent: str, content: str, fmt: str = 'md') -> str:
    """Generate a meaningful English filename from agent type and document content.
    Extracts ASCII words only — no Thai or non-Latin characters in filenames."""
    ext = fmt if fmt in converter.SUPPORTED_FORMATS else 'md'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    m = re.search(r'#\s*(.{3,60})', content)
    if m:
        # Keep only ASCII letters, digits, spaces — strip Thai and other non-ASCII
        ascii_only = re.sub(r'[^\x20-\x7E]', ' ', m.group(1).strip())
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', ascii_only)
        slug = slug.strip('_')[:30]
        if len(slug) >= 3:
            return f"{agent}_{slug}_{ts}.{ext}"
    return f"{agent}_{ts}.{ext}"


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
            if fname == '.gitkeep':
                continue
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


def handle_save(pending_doc: str, pending_agent: str, workspace: str,
                job_id=None, output_format: str = 'md'):
    """Save the pending document to workspace without another LLM call.
    Generator that yields SSE data strings."""
    try:
        filename = _suggest_filename(pending_agent, pending_doc, output_format)
        yield f"data: {json.dumps({'type': 'status', 'message': f'กำลังบันทึกไฟล์ {filename}...'})}\n\n"

        if output_format in ('md', 'txt'):
            # Text formats — use existing MCP tool path
            result = _execute_tool(workspace, 'create_file', {
                'filename': filename,
                'content': pending_doc
            })
            if _tool_result_is_error(result):
                logger.warning(f"Save failed for {filename}: {result}")
                yield f"data: {json.dumps({'type': 'save_failed', 'message': result, 'filename': filename})}\n\n"
                yield f"data: {json.dumps({'type': 'tool_result', 'tool': 'create_file', 'result': result})}\n\n"
                return
        else:
            # Binary formats — convert and write directly
            file_bytes = converter.convert(pending_doc, output_format)
            dest = os.path.join(workspace, filename)
            with open(dest, 'wb') as f:
                f.write(file_bytes)
            result = f"บันทึก {filename} เรียบร้อย"

        size = len(pending_doc.encode('utf-8')) if output_format in ('md', 'txt') else os.path.getsize(os.path.join(workspace, filename))
        db.record_file(job_id, filename, pending_agent, size)
        _notify_workspace_changed(workspace)
        yield f"data: {json.dumps({'type': 'text', 'content': f'✅ {result}'})}\n\n"
        yield f"data: {json.dumps({'type': 'tool_result', 'tool': 'create_file', 'result': result})}\n\n"
    except Exception as e:
        message = f'ไม่สามารถบันทึกไฟล์ได้: {str(e)}'
        logger.error(f"Unexpected save error: {e}")
        yield f"data: {json.dumps({'type': 'save_failed', 'message': message})}\n\n"


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


def handle_pm_save(temp_paths: list, workspace: str, job_id=None, output_format: str = 'md', output_formats: list = None):
    """Move all PM staged temp files to workspace. Generator that yields SSE data strings."""
    saved = []
    for i, temp_path in enumerate(temp_paths):
        # Per-file format: use output_formats[i] if provided, else fall back to output_format
        fmt = (output_formats[i] if output_formats and i < len(output_formats) else output_format)
        # Security: reject paths outside TEMP_DIR
        if not _is_safe_temp_path(temp_path):
            logger.warning(f"Rejected unsafe temp path: {temp_path}")
            continue
        if not os.path.isfile(temp_path):
            logger.warning(f"Temp file not found (expired?): {temp_path}")
            continue
        try:
            if fmt in ('md', 'txt'):
                filename = _move_to_workspace(temp_path, workspace)
                # Rename .md → .txt if needed
                if fmt == 'txt' and filename.endswith('.md'):
                    old_path = os.path.join(workspace, filename)
                    filename = filename[:-3] + '.txt'
                    os.rename(old_path, os.path.join(workspace, filename))
            else:
                # Read temp content, convert, write with new extension
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                base = os.path.splitext(os.path.basename(temp_path))[0]
                filename = f"{base}.{fmt}"
                file_bytes = converter.convert(content, fmt)
                dest = os.path.join(workspace, filename)
                with open(dest, 'wb') as f:
                    f.write(file_bytes)
                os.remove(temp_path)

            saved.append(filename)
            agent_prefix = filename.split('_')[0] if '_' in filename else 'pm'
            size = 0
            try:
                size = os.path.getsize(os.path.join(workspace, filename))
            except OSError:
                pass
            db.record_file(job_id, filename, agent_prefix, size)
            _notify_workspace_changed(workspace)
            yield f"data: {json.dumps({'type': 'tool_result', 'tool': 'create_file', 'result': f'บันทึก {filename} เรียบร้อย'})}\n\n"
        except Exception as e:
            logger.error(f"Failed to save temp file {temp_path}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'ไม่สามารถบันทึก {os.path.basename(temp_path)}: {str(e)}'})}\n\n"

    count = len(saved)
    if count > 0:
        names = ', '.join(saved)
        save_msg = '✅ บันทึก ' + str(count) + ' ไฟล์เรียบร้อย\n' + names
        yield f"data: {json.dumps({'type': 'text', 'content': save_msg})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'text', 'content': 'ไม่พบไฟล์ที่รอบันทึก (อาจหมดอายุแล้ว) กรุณาสร้างเอกสารใหม่'})}\n\n"


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_file('index.html')


@app.route('/history')
def history_page():
    return send_file('history.html')


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
    session_id         = request.json.get('session_id', None)
    output_format      = request.json.get('output_format', 'md').strip().lower()
    if output_format not in converter.SUPPORTED_FORMATS:
        output_format = 'md'
    output_formats     = request.json.get('output_formats', None)
    if isinstance(output_formats, list):
        output_formats = [f if f in converter.SUPPORTED_FORMATS else 'md' for f in output_formats]
    else:
        output_formats = None
    if not isinstance(pending_temp_paths, list):
        pending_temp_paths = []

    def generate():
        # Create a DB job record for this request (None if DB unavailable)
        job_id = db.create_job(user_input, session_id)

        with _workspace_lock:
            workspace = WORKSPACE_PATH
        os.makedirs(workspace, exist_ok=True)
        _cleanup_old_temp()

        # ── Follow-up: PM staged files waiting for confirmation ──────────────
        if pending_temp_paths:
            if _is_save_intent(user_input):
                for sse in handle_pm_save(pending_temp_paths, workspace, job_id, output_format, output_formats):
                    yield sse
                db.complete_job(job_id, '')
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            # Edit intent while PM files are pending — block and ask user to save/discard first
            if _is_edit_intent(user_input) and not _is_discard_intent(user_input):
                db.discard_job(job_id)
                yield f"data: {json.dumps({'type': 'text', 'content': 'คุณมีไฟล์รอบันทึกอยู่ กรุณาพิมพ์ **บันทึก** เพื่อบันทึกไฟล์ก่อน หรือ **ยกเลิก** เพื่อยกเลิกแล้วส่งคำสั่งใหม่'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            # Discard temp files regardless
            for tp in pending_temp_paths:
                if _is_safe_temp_path(tp) and os.path.isfile(tp):
                    os.remove(tp)
                    logger.info(f"Discarded temp file: {os.path.basename(tp)}")
            if _is_pure_discard(user_input):
                # Pure cancel keyword — just confirm and stop
                db.discard_job(job_id)
                yield f"data: {json.dumps({'type': 'text', 'content': '🗑️ ยกเลิกการบันทึกไฟล์เรียบร้อย'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            # New task alongside discard — notify briefly then fall through to Orchestrator
            yield f"data: {json.dumps({'type': 'status', 'message': '🗑️ ยกเลิกไฟล์เก่าแล้ว กำลังดำเนินการคำสั่งใหม่...'})}\n\n"

        # ── Follow-up: single-agent doc confirming/editing ───────────────────
        if pending_doc and pending_agent:
            if _is_save_intent(user_input):
                for sse in handle_save(pending_doc, pending_agent, workspace, job_id, output_format):
                    yield sse
                db.complete_job(job_id, pending_doc)
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            elif _is_discard_intent(user_input):
                if _is_pure_discard(user_input):
                    # Pure cancel keyword — just confirm and stop
                    db.discard_job(job_id)
                    yield f"data: {json.dumps({'type': 'text', 'content': '🗑️ ยกเลิกเอกสารแล้ว สามารถส่งคำสั่งใหม่ได้เลย'})}\n\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return
                # Has additional task content — notify briefly then fall through to Orchestrator
                yield f"data: {json.dumps({'type': 'status', 'message': '🗑️ ยกเลิกเอกสารเดิมแล้ว กำลังดำเนินการคำสั่งใหม่...'})}\n\n"
            elif _is_edit_intent(user_input):
                # Explicit edit instruction → revise the pending doc
                text_chunks = []
                for sse in handle_revise(pending_doc, pending_agent, user_input, workspace):
                    yield sse
                    if sse.startswith('data: '):
                        try:
                            d = json.loads(sse[6:])
                            if d.get('type') == 'text':
                                text_chunks.append(d.get('content', ''))
                        except Exception:
                            pass
                db.complete_job(job_id, ''.join(text_chunks))
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            else:
                # No save/discard/edit signal → treat as new task, discard pending doc silently
                yield f"data: {json.dumps({'type': 'status', 'message': '🗑️ ยกเลิกเอกสารเดิมแล้ว กำลังดำเนินการคำสั่งใหม่...'})}\n\n"
                # fall through to Orchestrator

        try:
            # Step 1: Orchestrator เลือก Agent
            yield f"data: {json.dumps({'type': 'status', 'message': 'กำลังวิเคราะห์งาน...'})}\n\n"

            _MAX_RETRIES = 3
            routing = None
            for _attempt in range(_MAX_RETRIES):
                _orch_messages = [
                    {"role": "system", "content": ORCHESTRATOR_PROMPT},
                    {"role": "user", "content": user_input}
                ]
                if _attempt > 0:
                    _orch_messages.append({"role": "user", "content": "ตอบกลับด้วย JSON เท่านั้น ห้ามมีข้อความอื่น"})
                    logger.warning(f"Orchestrator retry attempt {_attempt + 1}/{_MAX_RETRIES}")
                try:
                    orchestrator_response = client.chat.completions.create(
                        model=MODEL,
                        max_tokens=7500,
                        messages=_orch_messages
                    )
                except RateLimitError:
                    db.fail_job(job_id)
                    yield f"data: {json.dumps({'type': 'error', 'message': 'API ถูกใช้งานเกิน limit กรุณารอสักครู่แล้วลองใหม่'})}\n\n"
                    return
                except APITimeoutError:
                    db.fail_job(job_id)
                    yield f"data: {json.dumps({'type': 'error', 'message': 'API ใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง'})}\n\n"
                    return
                except APIError:
                    db.fail_job(job_id)
                    yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดจาก API กรุณาลองใหม่'})}\n\n"
                    return

                orch_choice = orchestrator_response.choices[0]
                if orch_choice.finish_reason == 'length':
                    logger.warning("Orchestrator response truncated by max_tokens")
                raw = orch_choice.message.content
                if not raw:
                    if _attempt == _MAX_RETRIES - 1:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ไม่ตอบกลับ กรุณาลองใหม่'})}\n\n"
                        return
                    continue
                try:
                    routing = json.loads(_extract_json(raw))
                    break
                except (json.JSONDecodeError, ValueError):
                    logger.warning(f"Orchestrator bad JSON (attempt {_attempt + 1}): {raw[:200]!r}")
                    if _attempt == _MAX_RETRIES - 1:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
                        return
            if routing is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
                return
            agent = routing.get('agent', 'hr')
            reason = routing.get('reason', '')

            db.update_job_agent(job_id, agent, reason)
            yield f"data: {json.dumps({'type': 'agent', 'agent': agent, 'reason': reason})}\n\n"

            # Step 2: Route to agent(s)
            if agent == 'pm':
                # PM path: decompose → multiple agents
                yield f"data: {json.dumps({'type': 'status', 'message': 'PM Agent กำลังวางแผนงาน...'})}\n\n"

                _pm_subtasks = None
                for _pm_attempt in range(_MAX_RETRIES):
                    _pm_messages = [
                        {"role": "system", "content": PM_PROMPT},
                        {"role": "user", "content": user_input}
                    ]
                    if _pm_attempt > 0:
                        _pm_messages.append({"role": "user", "content": "ตอบกลับด้วย JSON เท่านั้น ห้ามมีข้อความอื่น"})
                        logger.warning(f"PM Agent retry attempt {_pm_attempt + 1}/{_MAX_RETRIES}")
                    try:
                        pm_response = client.chat.completions.create(
                            model=MODEL,
                            max_tokens=6000,
                            messages=_pm_messages
                        )
                    except Exception as e:
                        logger.error(f"PM Agent API error: {e}")
                        db.fail_job(job_id)
                        yield f"data: {json.dumps({'type': 'error', 'message': 'PM Agent เกิดข้อผิดพลาด กรุณาลองใหม่'})}\n\n"
                        return

                    # Log finish_reason to detect future truncation issues
                    pm_choice = pm_response.choices[0]
                    if pm_choice.finish_reason == 'length':
                        logger.warning("PM Agent response truncated by max_tokens — consider increasing further")
                    else:
                        logger.info(f"PM Agent finish_reason: {pm_choice.finish_reason}")

                    raw_pm = pm_choice.message.content or ''
                    try:
                        pm_data = json.loads(_extract_json(raw_pm))
                        _pm_subtasks = pm_data.get('subtasks', [])
                        break
                    except (json.JSONDecodeError, ValueError):
                        logger.warning(f"PM Agent bad JSON (attempt {_pm_attempt + 1}): {raw_pm[:300]!r}")
                        if _pm_attempt == _MAX_RETRIES - 1:
                            yield f"data: {json.dumps({'type': 'error', 'message': 'PM Agent ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
                            return
                if _pm_subtasks is None:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'PM Agent ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
                    return
                subtasks = _pm_subtasks

                # Filter out invalid agents (e.g. 'pm' self-reference)
                valid_agents = {'hr', 'accounting', 'manager'}
                subtasks = [s for s in subtasks if s.get('agent') in valid_agents]

                if not subtasks:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'PM Agent ไม่สามารถแบ่งงานได้ กรุณาลองใหม่'})}\n\n"
                    return

                yield f"data: {json.dumps({'type': 'pm_plan', 'subtasks': subtasks})}\n\n"
                logger.info(f"PM Agent decomposed into {len(subtasks)} subtasks")

                all_pm_chunks = []  # collect all subtask output for DB
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

                    # Stream content to frontend AND capture it for temp staging + DB
                    subtask_chunks = []
                    subtask_failed = False
                    for sse_line in stream_agent(sub_prompt, sub_task, sub_label, sub_max_tokens):
                        yield sse_line
                        if sse_line.startswith('data: '):
                            try:
                                d = json.loads(sse_line[6:])
                                if d.get('type') == 'text':
                                    subtask_chunks.append(d.get('content', ''))
                                elif d.get('type') == 'error':
                                    subtask_failed = True
                            except Exception:
                                pass
                    if subtask_failed:
                        break

                    # Write captured content to temp staging (hidden from workspace/file panel)
                    full_content = ''.join(subtask_chunks)
                    all_pm_chunks.append(full_content)
                    if full_content.strip():
                        temp_path = _write_temp(full_content, sub_agent)
                        filename = os.path.basename(temp_path)
                        yield f"data: {json.dumps({'type': 'pending_file', 'temp_path': temp_path, 'filename': filename, 'agent': sub_agent})}\n\n"

                    yield f"data: {json.dumps({'type': 'subtask_done', 'agent': sub_agent, 'index': i, 'total': len(subtasks)})}\n\n"

                if subtask_failed:
                    db.fail_job(job_id)
                else:
                    db.complete_job(job_id, '\n\n---\n\n'.join(all_pm_chunks))

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
                yield f"data: {json.dumps({'type': 'status', 'message': f'{agent_label} กำลังตรวจสอบ workspace...'})}\n\n"

                text_chunks = []
                for sse_line in run_agent_with_tools(
                    system_prompt, user_input, workspace,
                    agent_label, agent_max_tokens,
                    tools=READ_ONLY_TOOLS
                ):
                    yield sse_line
                    if sse_line.startswith('data: '):
                        try:
                            d = json.loads(sse_line[6:])
                            if d.get('type') == 'text':
                                text_chunks.append(d.get('content', ''))
                        except Exception:
                            pass
                db.complete_job(job_id, ''.join(text_chunks))

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except json.JSONDecodeError:
            db.fail_job(job_id)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Orchestrator ตอบกลับผิดรูปแบบ กรุณาลองใหม่'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            db.fail_job(job_id)
            logger.error(f"Unexpected error in chat: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'เกิดข้อผิดพลาดจากระบบ กรุณาลองใหม่อีกครั้ง'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

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
    abs_path = _normalize_workspace_path(new_path)
    # Basic safety: reject suspiciously short paths (e.g. bare drive root "C:\")
    if len(abs_path) <= 3:
        return jsonify({'error': 'Path ไม่ปลอดภัย กรุณาระบุ directory ที่ชัดเจนกว่านี้'}), 400
    if not _is_allowed_workspace_path(abs_path):
        roots_str = ", ".join(_ALLOWED_ROOTS)
        return jsonify({
            'error': f'อนุญาตเฉพาะ workspace ภายใต้ directories ที่กำหนดไว้: {roots_str}'
        }), 400
    try:
        os.makedirs(abs_path, exist_ok=True)
    except OSError as e:
        return jsonify({'error': f'ไม่สามารถสร้าง directory ได้: {str(e)}'}), 400
    with _workspace_lock:
        WORKSPACE_PATH = abs_path
    logger.info(f"Workspace changed to: {abs_path}")
    return jsonify({'path': abs_path, 'exists': True})


@app.route('/api/workspaces', methods=['GET'])
def list_workspaces():
    """Return all available workspace directories grouped by allowed root."""
    with _workspace_lock:
        current = os.path.realpath(WORKSPACE_PATH)

    result = {'current': current, 'roots': []}
    for root in _ALLOWED_ROOTS:
        if not os.path.isdir(root):
            continue
        label = os.path.basename(root) or root
        workspaces = []
        try:
            for entry in sorted(os.scandir(root), key=lambda e: e.name.lower()):
                if entry.is_dir() and not entry.name.startswith('.'):
                    workspaces.append({
                        'path': entry.path,
                        'name': entry.name,
                        'active': os.path.realpath(entry.path) == current
                    })
        except PermissionError:
            pass
        result['roots'].append({'root': root, 'label': label, 'workspaces': workspaces})

    return jsonify(result)


@app.route('/api/workspace/new', methods=['POST'])
def create_workspace_folder():
    """Create a new workspace folder under an allowed root and switch to it."""
    import re as _re
    global WORKSPACE_PATH
    data = request.json or {}
    root = data.get('root', '').strip()
    name = data.get('name', '').strip()

    if not root or not name:
        return jsonify({'error': 'ระบุ root และ name ให้ครบ'}), 400
    if not _re.match(r'^[a-zA-Z0-9_-]{1,50}$', name):
        return jsonify({'error': 'ชื่อโฟลเดอร์ใช้ได้เฉพาะ a-z, A-Z, 0-9, _ และ - เท่านั้น (ไม่เกิน 50 ตัว)'}), 400

    real_root = os.path.realpath(root)
    if real_root not in [os.path.realpath(r) for r in _ALLOWED_ROOTS]:
        return jsonify({'error': 'root ไม่ได้รับอนุญาต'}), 400

    new_path = os.path.realpath(os.path.join(real_root, name))
    if os.path.dirname(new_path) != real_root:
        return jsonify({'error': 'ไม่อนุญาตให้สร้าง subdirectory ซ้อน'}), 400

    try:
        os.makedirs(new_path, exist_ok=True)
    except OSError as e:
        return jsonify({'error': f'ไม่สามารถสร้าง directory ได้: {str(e)}'}), 400

    with _workspace_lock:
        WORKSPACE_PATH = new_path
    logger.info(f"Workspace created and switched to: {new_path}")
    return jsonify({'path': new_path, 'name': name})


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

        # Register with global event bus so agent saves notify this client directly
        with _ws_change_lock:
            _ws_change_queues.setdefault(wp, []).append(event_queue)

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
            # Unregister from global event bus
            with _ws_change_lock:
                bucket = _ws_change_queues.get(wp, [])
                try:
                    bucket.remove(event_queue)
                except ValueError:
                    pass
                if not bucket:
                    _ws_change_queues.pop(wp, None)

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
        'workspace_exists': os.path.isdir(wp),
        'db': db.db_status()
    })


@app.route('/api/history')
def history():
    """Return the last 50 jobs with their saved files."""
    limit = min(int(request.args.get('limit', 50)), 200)
    return jsonify({'jobs': db.get_history(limit), 'db_available': db.DB_AVAILABLE})


@app.route('/api/history/<job_id>')
def history_job(job_id: str):
    """Return a single job with full output_text and files."""
    job = db.get_job(job_id)
    if not job:
        return jsonify({'error': 'ไม่พบประวัติงานนี้'}), 404
    return jsonify(job)


if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    # host='0.0.0.0' allows access from Windows browser when running in WSL
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    app.run(debug=debug_mode, host=host, port=5000, threaded=True)
