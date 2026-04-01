# Project Summary — Internal AI Assistant POC
> ไฟล์นี้ใช้เพื่อให้ AI เข้าใจภาพรวมทั้งโปรเจกต์อย่างรวดเร็ว

---

## โปรเจกต์คืออะไร

**Internal AI Assistant Platform** — ระบบ AI สำหรับพนักงานภายในบริษัทไทย
พนักงานพิมพ์งานเป็นภาษาไทย → AI เลือก Agent ที่เหมาะสม → สร้างเอกสาร (Draft) → User ยืนยัน → บันทึกเป็นไฟล์จริงในระบบ

- **Version ปัจจุบัน:** v0.32.9 (Sidebar session restore wiring)
- **สถานะ:** Production-Ready POC + Session Isolation + Multi-Format Export
- **Branch:** `wsl-experiment`
- **Last Commit:** v0.32.9 — fix: restore selected sidebar sessions

---

## ฟีเจอร์ที่มีแล้ว (v0.32.8)

| ฟีเจอร์ | สถานะ | หมายเหตุ |
|---|---|---|
| AI Agents 6 แผนก (HR, บัญชี, ผู้จัดการ, PM, Chat, Document) | ✅ ทำงานได้ | Document Agent เพิ่มใน v0.27.0 |
| Orchestrator — เลือก Agent อัตโนมัติจากคำถาม | ✅ ทำงานได้ | |
| Streaming response ผ่าน SSE | ✅ ทำงานได้ | |
| บันทึกไฟล์ใน server workspace | ✅ ทำงานได้ | |
| Per-session workspace isolation | ✅ ทำงานได้ | v0.32.7 ทำให้ file APIs ใช้ session scope ตรงกับ chat แล้ว |
| Workspace/file management routes | ✅ ทำงานได้ | `health/files/preview/serve/delete/workspace` รองรับ session workspace แล้ว |
| Local Agent Mode — ไฟล์บน Windows โดยตรง | ✅ ทำงานได้ | เพิ่มใน v0.23.0 |
| Sidebar แสดงไฟล์ใน workspace | ✅ ทำงานได้ | |
| Sidebar พับ/ขยายได้ (collapsible) | ✅ ทำงานได้ | |
| File Preview Panel | ✅ ทำงานได้ | เพิ่มใน v0.29.0 |
| Session management API | ✅ ทำงานได้ | `GET /api/sessions`, `GET /api/sessions/<session_id>` |
| Context Injection — inject file list + content ก่อนส่ง AI | ✅ ทำงานได้ | |
| Web Search (DuckDuckGo) | ✅ ทำงานได้ | |
| Multi-format export (md/txt/docx/xlsx/pdf) | ✅ ทำงานได้ | |
| ประวัติการสนทนา (SQLite) | ✅ ทำงานได้ | |
| History viewer (history.html) | ✅ ทำงานได้ | |
| Rate limiting (per-IP) | ✅ ทำงานได้ | เพิ่มใน v0.19.0 |
| Gunicorn + gevent deployment | ✅ ทำงานได้ | เพิ่มใน v0.18.0 |
| Delete with human-in-the-loop confirmation | ✅ ทำงานได้ | |
| File overwrite support | ✅ ทำงานได้ | |
| Confirmation flow (save/discard/edit) | ✅ ทำงานได้ | |
| Concurrency tests ผ่านทุก TC | ✅ ผ่านแล้ว | |
| CORS lockdown บน local_agent.py | ✅ ทำงานได้ | |
| Workspace path validation (defense-in-depth) | ✅ ทำงานได้ | |
| Job save status correctness (fail vs complete) | ✅ ทำงานได้ | |
| Bug fixes (29 fixes across 3 review rounds) | ✅ เสร็จแล้ว | Critical + High + Medium severity |

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
    │                                    │  shared → state กลาง + session workspace
    │                                    │  utils → execute_tool, format_sse
    │                                    └──────┬──────┘
    │                                    agents/ (HR/บัญชี/PM/ผจก./Chat/Document)
    │                                    └── base_agent.py (LLM loop + tools)
    │
    └── POST localhost:7000/files ──────→ local_agent.py (Windows)
            └── list/create/update/delete       └── sandbox: _validate_path()

```

**ไฟล์หลัก:**
1. **`app.py`** — Flask Routes, SSE streaming, request/response flow, confirmation flow
2. **`core/orchestrator.py`** — วิเคราะห์งานและเลือก Agent
3. **`core/agent_factory.py`** — สร้างและเรียกใช้ Agent objects
4. **`core/shared.py`** — global state (client, workspace, event bus, session workspaces)
5. **`core/utils.py`** — `load_prompt`, `execute_tool`, `format_sse`
6. **`agents/base_agent.py`** — agentic loop (stream + tool calls)
7. **`agents/`** — `hr_agent.py`, `accounting_agent.py`, `manager_agent.py`, `pm_agent.py`, `chat_agent.py`, `document_agent.py`
8. **`prompts/`** — System prompts แยกเป็น `.md` ต่อ Agent
9. **`local_agent.py`** — HTTP server (port 7000) บน Windows, stdlib only
10. **`db.py`** — SQLite: jobs + saved_files
11. **`converter.py`** — แปลง Markdown → PDF/DOCX/XLSX/TXT
12. **`mcp_server.py`** — Filesystem tools (Layer A: functions, Layer B: FastMCP)
13. **`gunicorn.conf.py`** — Gunicorn config (gevent workers, SSE-compatible)

---

## เทคโนโลยีหลัก

- **Backend:** Flask (Python 3.11) + Gunicorn (gevent workers)
- **AI:** OpenRouter API (Claude 4.5 Sonnet)
- **Frontend:** Vanilla HTML/JS/CSS เป็นตัวหลัก + มี Next.js frontend ระหว่าง migration
- **Persistence:** SQLite (db.py, WAL mode) + Workspace Filesystem
- **Streaming:** SSE (Server-Sent Events) + `stream_with_context`
- **Local Agent:** `local_agent.py` (stdlib only) + browser middleware
- **Testing:** `smoke_test_phase0.py`, `test_cases.py`, `test_concurrency_pm.py`, `quick-demo-check.py`
- **Rate Limiting:** flask-limiter (per-IP on chat and delete endpoints)

---

## Known Limitations

- **No authentication** — ไม่มีระบบ login หรือ role-based access control
- **SQLite** — ไม่รองรับ concurrent writes สูง; ใช้ WAL mode เพื่อลดปัญหา
- **No CSRF protection** — ไม่มี CSRF token validation
- **No formal test framework** — ใช้ script-based integration tests, ไม่มี pytest/unittest
- **No linting or formatting tools** — ไม่มี pylint, flake8, black, mypy
- **PDF character limit** — PDF export จำกัดที่ 100,000 characters
- **Local Agent mode is Windows-only** — `local_agent.py` ออกแบบสำหรับ Windows
- **`_session_workspaces` dict has no TTL eviction** — memory grows with session count (minor, only matters at very high concurrency)
- **Next.js build ยังพึ่ง Google Fonts** — ใน environment ที่ออก internet ไม่ได้ `npm run build` จะ fail จนกว่าจะเปลี่ยน font strategy

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
