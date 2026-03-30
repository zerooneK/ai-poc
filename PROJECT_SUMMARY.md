# Project Summary — Internal AI Assistant POC
> ไฟล์นี้ใช้เพื่อให้ AI เข้าใจภาพรวมทั้งโปรเจกต์อย่างรวดเร็ว

---

## โปรเจกต์คืออะไร

**Internal AI Assistant Platform** — ระบบ AI สำหรับพนักงานภายในบริษัทไทย
พนักงานพิมพ์งานเป็นภาษาไทย → AI เลือก Agent ที่เหมาะสม → สร้างเอกสาร (Draft) → User ยืนยัน → บันทึกเป็นไฟล์จริงในระบบ

- **Version ปัจจุบัน:** v0.25.2 (Remove noisy pending modal for single-agent)
- **สถานะ:** Prototype Ready + Security Hardened + Demo Preparation
- **Branch:** `wsl-experiment`
- **Last Commit:** v0.24.3 — fix: inject CE year + English date so AI searches correct year

---

## ฟีเจอร์ที่มีแล้ว (v0.24.1)

| ฟีเจอร์ | สถานะ |
|---|---|
| AI Agents 5 แผนก (HR, บัญชี, ผู้จัดการ, PM, Chat) | ✅ ทำงานได้ |
| Orchestrator — เลือก Agent อัตโนมัติจากคำถาม | ✅ ทำงานได้ |
| Streaming response ผ่าน SSE | ✅ ทำงานได้ |
| บันทึกไฟล์ใน server workspace (WSL) | ✅ ทำงานได้ |
| Local Agent Mode — ไฟล์บน Windows โดยตรง | ✅ ทำงานได้ |
| Sidebar แสดงไฟล์ใน workspace (server + local) | ✅ ทำงานได้ |
| Sidebar พับ/ขยายได้ (collapsible) | ✅ ทำงานได้ |
| Context Injection — inject file list + content ก่อนส่ง AI | ✅ ทำงานได้ |
| Web Search ในระหว่างตอบ | ✅ ทำงานได้ |
| ประวัติการสนทนา (SQLite) | ✅ ทำงานได้ |
| Export PDF/DOCX ผ่าน converter.py | ✅ ทำงานได้ |
| History viewer (history.html) | ✅ ทำงานได้ |
| Concurrency tests ผ่านทุก TC | ✅ ผ่านแล้ว |
| CORS lockdown บน local_agent.py | ✅ ทำงานได้ |
| Workspace path validation (defense-in-depth) | ✅ ทำงานได้ |
| Job save status correctness (fail vs complete) | ✅ ทำงานได้ |

---

## สถาปัตยกรรม (Modular Architecture)

```
Browser (index.html)
    │
    ├── POST /api/chat ──────────────────→ Flask (app.py)
    │       └── SSE stream back                 │
    │                                    ┌──────┴──────┐
    │                                    │  core/      │
    │                                    │  orchestrator → เลือก Agent
    │                                    │  agent_factory → สร้าง Agent
    │                                    │  shared → state กลาง
    │                                    │  utils → execute_tool, format_sse
    │                                    └──────┬──────┘
    │                                    agents/ (HR/บัญชี/PM/ผจก./Chat)
    │                                    └── base_agent.py (LLM loop + tools)
    │
    └── POST localhost:7000/files ──────→ local_agent.py (Windows)
            └── list/create/update/delete       └── sandbox: _validate_path()

```

**ไฟล์หลัก:**
1. **`app.py`** — Flask Routes, SSE streaming, request/response flow
2. **`core/orchestrator.py`** — วิเคราะห์งานและเลือก Agent
3. **`core/agent_factory.py`** — สร้างและเรียกใช้ Agent objects
4. **`core/shared.py`** — global state (client, workspace, event bus)
5. **`core/utils.py`** — `load_prompt`, `execute_tool`, `format_sse`
6. **`agents/base_agent.py`** — agentic loop (stream + tool calls)
7. **`agents/`** — `hr_agent.py`, `accounting_agent.py`, `manager_agent.py`, `pm_agent.py`, `chat_agent.py`
8. **`prompts/`** — System prompts แยกเป็น `.md` ต่อ Agent
9. **`local_agent.py`** — HTTP server (port 7000) บน Windows, stdlib only
10. **`db.py`** — SQLite: sessions + conversation history
11. **`converter.py`** — แปลง Markdown → PDF/DOCX

---

## เทคโนโลยีหลัก

- **Backend:** Flask (Python 3.11)
- **AI:** OpenRouter API (Claude 3.5 Sonnet / 4.5)
- **Frontend:** Vanilla HTML/JS/CSS (Silent Concierge Design)
- **Persistence:** SQLite (db.py) + Workspace Filesystem
- **Streaming:** SSE (Server-Sent Events) + `stream_with_context`
- **Local Agent:** `local_agent.py` (stdlib only) + browser middleware
- **Testing:** `smoke_test_phase0.py`, `test_cases.py`, `test_concurrency_pm.py`

---

## Local Agent Mode — วิธีทำงาน

เมื่อ `local_agent.py` รันบน Windows (port 7000):
1. Browser detect → แสดง "Local" badge + แสดง Windows path ใน header
2. Sidebar หยุด SSE จาก server → poll `localhost:7000/files` ทุก 3 วินาทีแทน
3. ก่อนส่งทุก message → browser inject file list + เนื้อหาไฟล์ text (≤50KB) เข้า context
4. Flask รับ flag `local_agent_mode:true` → ใช้ `LOCAL_AGENT_TOOLS` (web_search + local_delete เท่านั้น)
5. การสร้าง/แก้ไขไฟล์ → browser intercept SSE `save_document` → ส่งไป `localhost:7000`
6. การลบไฟล์ → AI เรียก `local_delete` → server ส่ง SSE event → browser ลบผ่าน `localhost:7000`

---

## กฎสำคัญในการพัฒนา (Strict Rules)

1.  **ภาษา:** ทุกอย่างที่ User เห็นต้องเป็น **ภาษาไทย**
2.  **ชื่อไฟล์:** ไฟล์ใน workspace ต้องเป็น **English snake_case** เท่านั้น
3.  **ความปลอดภัย:** ตรวจสอบ Path ผ่าน `_is_allowed_workspace_path` / `_validate_path()` เสมอ
4.  **Version Control:** Bump version ทุกครั้งที่มีการแก้โค้ด และบันทึกลง CHANGELOG.md
5.  **Modular:** ห้ามใส่ Business Logic ยาวๆ ใน `app.py` ให้แยกเป็น Agent หรือ Core โมดูล
6.  **SSE Safety:** generators ทั้งหมดต้อง wrap ด้วย `stream_with_context` — ป้องกัน crash บน Gunicorn
7.  **Error Messages:** ห้าม leak `str(e)` ออก frontend — ใช้ Thai user-friendly message + log traceback
