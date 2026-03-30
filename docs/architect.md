# Architecture — Internal AI Assistant POC
> เอกสารนี้อธิบายสถาปัตยกรรมทางเทคนิคทั้งหมดของโปรเจกต์
> อัปเดตล่าสุด: v0.23.0 (30 มีนาคม 2569)

---

## ภาพรวมระบบ (System Overview)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                          │
│                          index.html                             │
│    ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│    │  Chat UI     │  │  File Sidebar │  │  Save Intercept  │   │
│    │  (SSE recv)  │  │  (poll/SSE)   │  │  (local agent)   │   │
│    └──────┬───────┘  └───────┬───────┘  └────────┬─────────┘   │
└───────────┼──────────────────┼───────────────────┼─────────────┘
            │                  │                   │
            │ POST /api/chat   │ GET /files/stream │ POST /files
            ▼ (SSE response)   ▼ (SSE)             ▼ (JSON)
┌───────────────────────────┐          ┌──────────────────────────┐
│      Flask Server (WSL)   │          │  local_agent.py (Windows)│
│         app.py            │          │     localhost:7000        │
│                           │          │                          │
│  ┌─────────────────────┐  │          │  - fs_list_files()       │
│  │   core/             │  │          │  - fs_create_file()      │
│  │   orchestrator.py   │  │          │  - fs_read_file()        │
│  │   agent_factory.py  │  │          │  - fs_update_file()      │
│  │   shared.py         │  │          │  - fs_delete_file()      │
│  │   utils.py          │  │          │  - _validate_path()      │
│  └────────┬────────────┘  │          └──────────────────────────┘
│           │               │
│  ┌────────▼────────────┐  │   ┌──────────────────┐
│  │   agents/           │  │   │  OpenRouter API   │
│  │   base_agent.py     │◄─┼───►  (Claude 3.5/4.5) │
│  │   hr_agent.py       │  │   └──────────────────┘
│  │   accounting_agent  │  │
│  │   manager_agent     │  │   ┌──────────────────┐
│  │   pm_agent.py       │  │   │  SQLite (db.py)  │
│  │   chat_agent.py     │  │◄──►  sessions +      │
│  └─────────────────────┘  │   │  history         │
│                           │   └──────────────────┘
│  workspace/ (WSL files)   │
└───────────────────────────┘
```

---

## Component ทั้งหมด

### 1. Frontend — `index.html`

Single-page app เขียนด้วย Vanilla HTML/CSS/JavaScript ไม่มี framework

**ความรับผิดชอบหลัก:**
- รับ input จาก user และส่งไปยัง `/api/chat`
- รับ SSE stream และแสดงผลแบบ real-time
- แสดงไฟล์ใน sidebar (server mode: SSE / local mode: polling)
- Intercept การบันทึกเอกสาร → ส่งไป `local_agent.py` เมื่ออยู่ใน Local Agent Mode
- Inject context (file list + content) ก่อนส่งทุก message ใน Local Agent Mode

**Mode การทำงาน 2 แบบ:**
| | Server Mode | Local Agent Mode |
|---|---|---|
| ตรวจจับไฟล์ | SSE `/api/workspace/files/stream` | Poll `localhost:7000/files` ทุก 3s |
| บันทึกไฟล์ | SSE → Flask → `workspace/` | Browser → `localhost:7000` |
| Context | ไม่ inject | Inject file list + text content ≤50KB |
| Tools ที่ AI ใช้ | `READ_ONLY_TOOLS` | `LOCAL_AGENT_TOOLS` |

---

### 2. Flask Backend — `app.py`

Entry point หลัก จัดการ HTTP routes และ SSE streaming

**Routes หลัก:**
| Route | Method | ทำอะไร |
|---|---|---|
| `/api/chat` | POST | รับ message → orchestrate → stream SSE กลับ |
| `/api/workspace/files/stream` | GET | SSE stream เมื่อไฟล์ใน workspace เปลี่ยน |
| `/api/workspace/files` | GET | List ไฟล์ใน workspace |
| `/api/workspace/save` | POST | บันทึก document ที่ user confirm |
| `/api/sessions` | GET/POST | จัดการ session |
| `/api/history` | GET | ดึง conversation history |
| `/api/convert` | POST | แปลง Markdown → PDF/DOCX |

**Tool Sets:**
```python
READ_ONLY_TOOLS      # web_search + list_files + read_file
LOCAL_AGENT_TOOLS    # web_search + local_delete (เมื่อ local_agent_mode=true)
MCP_TOOLS            # ทุก tool รวม create/update/delete (server workspace เท่านั้น)
```

---

### 3. Core Modules — `core/`

#### `core/orchestrator.py`
- รับ user message → เรียก LLM ด้วย prompt จาก `prompts/orchestrator.md`
- ตัดสินใจว่าจะใช้ Agent ไหน (hr / accounting / manager / pm / chat)
- Return: ชื่อ agent + parsed intent

#### `core/agent_factory.py`
- รับ agent name จาก orchestrator
- สร้าง agent instance และเรียก `run_with_tools()` หรือ `stream_response()`
- จัดการ conversation history ต่อ session

#### `core/shared.py`
- Global state: OpenAI client, workspace path, allowed roots
- Event bus สำหรับ notify workspace changes → SSE stream

#### `core/utils.py`
- `load_prompt(name)` — อ่าน prompt จาก `prompts/*.md`
- `execute_tool(workspace, tool_name, args)` — dispatch tool calls
- `format_sse(data)` — format JSON เป็น SSE `data:` line
- `extract_web_sources(result)` — parse web search results

---

### 4. Agents — `agents/`

#### `agents/base_agent.py`
คลาสแม่ที่ทุก agent สืบทอด มี 2 method หลัก:

```
stream_response()      — Simple streaming ไม่มี tools
run_with_tools()       — Agentic loop:
    loop (max 5 iterations):
        1. เรียก LLM พร้อม tools
        2. Stream text กลับ user
        3. ถ้า LLM เรียก tool → execute_tool() → ส่ง result กลับ LLM
        4. ถ้าไม่มี tool call → จบ loop
```

**Tool Call Flow:**
```
LLM output (tool_call)
    → base_agent สะสม chunks
    → execute_tool() ใน core/utils.py
    → append tool result ใน messages
    → LLM รอบถัดไป
```

#### Agents เฉพาะทาง:
| Agent | ไฟล์ | ความเชี่ยวชาญ |
|---|---|---|
| HR Agent | `hr_agent.py` | เอกสาร HR: ใบลา, นโยบาย, คำสั่งแต่งตั้ง |
| Accounting Agent | `accounting_agent.py` | เอกสารบัญชี: ใบสำคัญ, รายงานค่าใช้จ่าย |
| Manager Agent | `manager_agent.py` | บันทึกผู้บริหาร, approval, รายงาน |
| PM Agent | `pm_agent.py` | แผนงาน, status report, risk log |
| Chat Agent | `chat_agent.py` | สนทนาทั่วไป, ตอบคำถาม |

---

### 5. Local Agent — `local_agent.py`

HTTP server รันบนเครื่อง user (Windows) ด้วย Python stdlib เท่านั้น (ไม่มี dependencies)

**Port:** 7000 (default)

**Security:**
- `_validate_path()` — block path traversal (`../../` ฯลฯ)
- รับ request จาก `127.0.0.1` เท่านั้น
- Sandbox ภายใน workspace directory ที่กำหนด

**Endpoints:**
```
GET  /health     — ตรวจสอบ status + workspace ปัจจุบัน
POST /files      — { action: list|create|read|update|delete, filename?, content? }
```

**CORS:** อนุญาต `localhost:5000` เท่านั้น

---

### 6. Database — `db.py`

SQLite database สำหรับเก็บ conversation history

**Tables:**
```sql
sessions (id, created_at, title, agent_used)
messages (id, session_id, role, content, created_at, agent_used)
```

---

### 7. Converter — `converter.py`

แปลง Markdown เป็น PDF หรือ DOCX

- **PDF:** WeasyPrint
- **DOCX:** python-docx
- รองรับ Thai fonts

---

## Data Flow — Request ปกติ (Server Mode)

```
1. User พิมพ์ข้อความ
2. Browser POST /api/chat { message, session_id, history }
3. Flask → Orchestrator.analyze(message)
4. Orchestrator เรียก LLM → return { agent: "hr", intent: "..." }
5. Flask → AgentFactory.run(agent, message, history)
6. Agent เรียก LLM + tools (stream)
7. Flask yield format_sse(chunk) → SSE stream
8. Browser append text ใน chat bubble
9. เมื่อ AI เสร็จ → Browser แสดงปุ่ม "บันทึก"
10. User กด "บันทึก" → POST /api/workspace/save
11. Flask บันทึกไฟล์ใน workspace/
12. Watchdog detect → SSE notify → Sidebar refresh
```

---

## Data Flow — Local Agent Mode

```
1. User รัน local_agent.py บน Windows
2. Browser detect localhost:7000/health → เปิด Local Agent Mode
3. Browser แสดง Windows path ใน header, poll /files ทุก 3s
4. User พิมพ์ข้อความ
5. Browser fetch file list + content จาก localhost:7000
6. Browser inject context + POST /api/chat { local_agent_mode: true }
7. Flask ใช้ LOCAL_AGENT_TOOLS (web_search + local_delete เท่านั้น)
8. AI ตอบโดยใช้ context ที่ inject มา (ไม่ต้องเรียก list_files/read_file)
9. AI สร้าง document → SSE event { type: "save_document" }
10. Browser intercept → POST localhost:7000/files { action: create/update }
11. local_agent.py บันทึกไฟล์บน Windows โดยตรง
12. Browser poll ตรวจพบไฟล์ใหม่ → Sidebar refresh
```

---

## Deployment

### Development (ปัจจุบัน)
```bash
./start.sh          # รัน Flask บน localhost:5000
python local_agent.py   # รันบน Windows (port 7000)
```

### Production (แนะนำในอนาคต)
- Gunicorn + Nginx (config พร้อมใน `gunicorn.conf.py`, `nginx.conf`)
- ต้อง wrap SSE generators ด้วย `stream_with_context` (ทำแล้ว)
- ต้องตั้ง `_ALLOWED_ROOTS` ให้ถูกต้องบน production server

---

## ข้อจำกัดปัจจุบัน & สิ่งที่ควรพัฒนาต่อ

| ข้อจำกัด | คำอธิบาย | Priority |
|---|---|---|
| ไม่มี Authentication | ใครก็เข้า localhost:5000 ได้ | สูง |
| Local Agent ไม่มี Error UI | ถ้า port 7000 ไม่ตอบ ไม่มี feedback ชัดเจน | กลาง |
| History UI ยังพื้นฐาน | มีข้อมูลใน SQLite แต่ UI ยังไม่ครบ | กลาง |
| Export รองรับแค่ MD/PDF/DOCX | ไม่รองรับ Excel หรือ format อื่น | ต่ำ |
| Single-user | ไม่มี multi-user / role-based access | สูง (production) |
| Audit Log | ไม่มีบันทึกว่าใครแก้ไขอะไรเมื่อไหร่ | สูง (production) |
