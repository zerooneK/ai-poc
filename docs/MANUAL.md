# Developer Manual — AI Assistant Internal POC

> เอกสารนี้อธิบายโครงสร้างโค้ดทั้งหมดของระบบ สำหรับนักพัฒนาที่ต้องการเข้าใจว่าแต่ละส่วนทำงานอย่างไรและเชื่อมต่อกันอย่างไร
>
> **อัปเดตล่าสุด:** 2026-03-27 — v0.20.0

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [File Structure & Purpose](#3-file-structure--purpose)
4. [Core Components (detailed)](#4-core-components-detailed)
   - [app.py](#41-apppy)
   - [core/shared.py](#42-coresharedpy)
   - [core/orchestrator.py](#43-coreorchestratorpy)
   - [core/utils.py](#44-coreutilspy)
   - [core/agent_factory.py](#45-coreagent_factorypy)
   - [agents/base_agent.py](#46-agentsbase_agentpy)
   - [agents/ (each agent)](#47-agents-each-agent)
   - [db.py](#48-dbpy)
   - [mcp_server.py](#49-mcp_serverpy)
   - [converter.py](#410-converterpy)
5. [SSE Event Reference](#5-sse-event-reference)
6. [Frontend State Variables](#6-frontend-state-variables-indexhtml)
7. [Configuration Reference](#7-configuration-reference)
8. [Common Flows (step-by-step)](#8-common-flows-step-by-step)
9. [Known Risks & Constraints](#9-known-risks--constraints)

---

## 1. Project Overview

ระบบ **AI Assistant Internal POC** คือ web application ที่ช่วยพนักงานภายในบริษัทสร้างเอกสารและขอคำปรึกษาผ่าน AI โดยรองรับงาน 4 ประเภทหลัก:

| งาน | Agent | ตัวอย่าง |
|-----|-------|---------|
| งาน HR | HR Agent | ร่างสัญญาจ้าง, JD, อีเมลนโยบาย |
| งานบัญชี/การเงิน | Accounting Agent | Invoice, รายงานการเงิน |
| คำปรึกษาผู้บริหาร | Manager Advisor | Feedback พนักงาน, Headcount Request |
| งานข้ามแผนก | PM Agent | Onboarding ที่ต้องการทั้งเอกสาร HR + Invoice |

ระบบรองรับ:
- การ streaming ผลลัพธ์แบบ real-time ผ่าน SSE (Server-Sent Events)
- การบันทึกไฟล์ใน workspace หลายรูปแบบ (.md, .txt, .docx, .xlsx, .pdf)
- การค้นหาข้อมูลจากอินเทอร์เน็ต (DuckDuckGo)
- ประวัติการใช้งาน (SQLite)

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x, Flask, flask-limiter |
| AI API | OpenRouter (รองรับ model ใดก็ได้ เช่น claude-sonnet-4-5) |
| Database | SQLite 3 (WAL mode) |
| File Tools | MCP filesystem functions (ใน mcp_server.py) |
| Web Search | DuckDuckGo (ddgs library) |
| Document Export | python-docx, openpyxl, weasyprint, markdown |
| Frontend | Vanilla JS + marked.js (Markdown renderer) + Material Symbols |
| Streaming | Server-Sent Events (SSE) — `text/event-stream` |

---

## 2. Architecture Overview

### Component Diagram

```
Browser (index.html)
  │
  │  POST /api/chat (JSON)
  ▼
Flask app.py
  │
  ├── Confirmation Flow Handler
  │     (save / discard / revise / PM save)
  │
  ├── Orchestrator (core/orchestrator.py)
  │     LLM call → returns { agent, reason }
  │
  ├── AgentFactory (core/agent_factory.py)
  │     singleton cache → returns agent instance
  │
  ├── PMAgent.plan()  ─────────────────────────────┐
  │     LLM call → returns list of subtasks        │
  │                                                │
  └── Agent.run_with_tools() / stream_response()   │
        (HR / Accounting / Manager / Chat / PM)    │
        ├── LLM streaming call                     │
        ├── Tool calls → core/utils.execute_tool() │
        │   └── mcp_server.py functions            │
        └── yields SSE dicts                       │
                                                   │
  PM flow: iterates subtasks ◄─────────────────────┘
      each sub-agent writes temp file
      frontend gets pending_file events
      user confirms → handle_pm_save()

  SSE stream → Browser EventReader loop
    processes events:
      status, agent, pm_plan, text, tool_result,
      web_search_sources, pending_file, subtask_done,
      text_replace, save_failed, error, done

  GET /api/files/stream (SSE)
  ├── watchdog.Observer watches workspace dir
  └── pushes 'files' event on any change

Workspace files:
  workspace/  ← final saved documents
  temp/       ← PM subtask drafts (staged before user confirm)
  data/       ← assistant.db (SQLite)
```

### Data Flow: User Request

```
User types message → sendMessage() [JS]
  │
  ├─ intercept check: pending doc + save/cancel/edit intent?
  │     └─ yes → modal or direct action, no API call
  │
  ▼
POST /api/chat { message, pending_doc?, pending_temp_paths?,
                 conversation_history, output_format, session_id }
  │
  ▼
generate() [Flask SSE generator]
  │
  ├─ pending_temp_paths check (PM save flow)
  ├─ pending_doc check (single-agent save flow)
  │
  ▼
Orchestrator.route(user_input, history)
  │  LLM → JSON { agent: 'hr', reason: '...' }
  ▼
AgentFactory.get_agent(agent_type)
  │
  ├── if pm:
  │     PMAgent.plan() → subtasks[]
  │     for each subtask:
  │       sub_agent.stream_response() → text chunks
  │       _write_temp(content) → temp file
  │       yield pending_file SSE
  │
  └── else:
        agent.run_with_tools() → SSE dicts
          (may call list_files, read_file, web_search)
  │
  ▼
yield format_sse(event_dict)   ← each event encoded as SSE
  │
  ▼
Browser EventReader loop → update DOM
```

---

## 3. File Structure & Purpose

```
ai-poc-wsl/
├── app.py                  Flask entry point, routes, confirmation flow, SSE generator
├── db.py                   SQLite layer — jobs + saved_files tables, graceful degradation
├── mcp_server.py           Filesystem tools (create/read/update/delete/list files)
├── converter.py            Markdown → .txt/.docx/.xlsx/.pdf export
├── index.html              Single-page UI — chat, streaming, modals, file panel
├── history.html            Job history viewer page
├── start.sh                Quick start script (runs Flask)
├── setup.sh                One-time setup (venv, dependencies)
├── smoke_test_phase0.py    Automated smoke tests for Phase 0
├── test_cases.py           Use-case integration tests
│
├── core/
│   ├── shared.py           Singleton state: OpenAI client, workspace path, event bus
│   ├── orchestrator.py     Routes user input to the correct agent via LLM
│   ├── utils.py            load_prompt(), execute_tool(), format_sse(), web search
│   └── agent_factory.py    Thread-safe agent singleton cache
│
├── agents/
│   ├── base_agent.py       BaseAgent class — stream_response(), run_with_tools()
│   ├── hr_agent.py         HR Agent (สัญญาจ้าง, JD, นโยบาย)
│   ├── accounting_agent.py Accounting Agent (Invoice, รายงานการเงิน)
│   ├── manager_agent.py    Manager Advisor (Feedback, Headcount)
│   ├── pm_agent.py         PM Agent (วางแผนงาน, แบ่ง subtasks)
│   └── chat_agent.py       Chat Agent (สนทนาทั่วไป, คำถามระบบ)
│
├── prompts/
│   ├── orchestrator.md     System prompt สำหรับ Orchestrator
│   ├── hr_agent.md         System prompt สำหรับ HR Agent
│   ├── accounting_agent.md System prompt สำหรับ Accounting Agent
│   ├── manager_agent.md    System prompt สำหรับ Manager Advisor
│   ├── pm_agent.md         System prompt สำหรับ PM Agent
│   └── chat_agent.md       System prompt สำหรับ Chat Agent
│
├── workspace/              ไฟล์เอกสารที่บันทึกแล้ว (final)
├── temp/                   ไฟล์ draft ของ PM subtasks (รอ user confirm)
│   └── .gitkeep
├── data/
│   └── assistant.db        SQLite database
│
├── docs/
│   ├── poc-plan.md         POC plan, session logs, checklists
│   ├── project-plan.md     Full production plan, phases, risk register
│   └── MANUAL.md           [ไฟล์นี้] Developer manual
│
├── .claude/agents/         Subagent definitions สำหรับ Claude Code
├── .env                    Secret config (ห้าม commit)
├── .env.example            Template config
├── CLAUDE.md               Instructions สำหรับ Claude AI assistant
└── CHANGELOG.md            Version history
```

---

## 4. Core Components (detailed)

### 4.1 app.py

ไฟล์หลักของ Flask application — จัดการ routes, confirmation flow, และ SSE generator

#### Helper Functions

##### `_extract_json(raw: str) -> str`
ดึง JSON object ออกจาก LLM output ที่อาจมี markdown fences หรือ prose ล้อมรอบ
- ใช้ regex ลบ code fence `` ``` `` แล้วหา `{...}` ด้วย `find/rfind`
- Raises `ValueError` ถ้าไม่พบ JSON

##### `_normalize_workspace_path(path: str) -> str`
แปลง path ให้เป็น absolute path
- ถ้า `path` ว่าง ใช้ `_DEFAULT_WORKSPACE`

##### `_is_allowed_workspace_path(path: str) -> bool`
ตรวจว่า path อยู่ภายใต้ `_ALLOWED_ROOTS` ที่กำหนดใน env หรือไม่
- ป้องกัน user เปลี่ยน workspace ไปที่อันตราย (เช่น /)

##### Intent Detection Functions

```python
_is_save_intent(message)    # "บันทึก", "ยืนยัน", "ok", "save" ฯลฯ
_is_discard_intent(message) # "ยกเลิก", "cancel", "ไม่เอา" ฯลฯ
_is_pure_discard(message)   # ต้องตรง keyword เป๊ะๆ (substring ไม่นับ)
_is_edit_intent(message)    # "แก้ไข", "ปรับ", "edit", "modify" ฯลฯ
```

> **หมายเหตุ C1 Bug Fix:** คำว่า "ok" และ "save" ใน English ใช้ `\bword-boundary\b` ป้องกัน false positive เช่น "ok" ใน "stock"

##### `_suggest_filename(agent, content, fmt) -> str`
สร้างชื่อไฟล์อัตโนมัติ:
- ดึง H1 heading จาก content (ถ้ามี) มาทำ slug ASCII
- รูปแบบ: `{agent}_{slug}_{timestamp}.{ext}`
- ตัวอย่าง: `hr_employment_contract_20250101_123456.md`

##### `_write_temp(content, agent) -> str`
เขียน content ลง `temp/` directory แล้วคืน absolute path ของไฟล์

##### `_move_to_workspace(temp_path, workspace) -> str`
ย้ายไฟล์จาก `temp/` ไป `workspace/` โดยใช้ `os.replace()` (atomic)

##### `_cleanup_old_temp()`
ลบไฟล์ใน `temp/` ที่เก่ากว่า 1 ชั่วโมง (เรียกทุกครั้งที่มี request ใหม่)

##### `handle_save(pending_doc, pending_agent, workspace, job_id, output_format)`
**Generator** — จัดการบันทึกเอกสาร single-agent:
1. สร้างชื่อไฟล์ด้วย `_suggest_filename()`
2. ถ้า format คือ `md/txt` → ใช้ `execute_tool('create_file')`
3. ถ้า format อื่น → ใช้ `converter.convert()` แล้วเขียน binary
4. บันทึกลง DB และ notify workspace watchers
5. yield SSE events: `status`, `text` (ผลลัพธ์), `tool_result`

##### `handle_revise(pending_doc, pending_agent, instruction, history)`
**Generator** — แก้ไขเอกสารที่ pending:
- สร้าง revise prompt: `"แก้ไขเอกสาร... คำสั่ง: {instruction} เอกสารเดิม: {doc}"`
- เรียก `agent_instance.stream_response()` แบบ yield

##### `handle_pm_save(temp_paths, workspace, job_id, output_format, output_formats, agent_types)`
**Generator** — บันทึกหลายไฟล์พร้อมกัน (PM flow):
- ตรวจความปลอดภัยของ `temp_path` ทุกไฟล์ด้วย `_is_safe_temp_path()`
- ย้ายหรือ convert แต่ละไฟล์ไป workspace
- yield `tool_result` SSE ต่อไฟล์, yield `text` สรุปท้ายสุด

#### MCP_TOOLS List

```python
MCP_TOOLS = [
    create_file    # สร้างไฟล์ใหม่
    read_file      # อ่านไฟล์
    update_file    # แก้ไขไฟล์ (เขียนทับ)
    delete_file    # ลบไฟล์
    list_files     # แสดงรายการ
    web_search     # ค้นหาอินเทอร์เน็ต (DuckDuckGo)
]

READ_ONLY_TOOLS = [list_files, read_file, web_search]
# ใช้กับ agents ปกติ (ไม่มีสิทธิ์ write ตรงๆ — ระบบจัดการ save ให้)
```

#### Routes

| Method | Path | Rate Limit | Description |
|--------|------|-----------|-------------|
| GET | `/` | - | Serve index.html |
| GET | `/history` | - | Serve history.html |
| POST | `/api/chat` | 10/min (env) | Main chat endpoint — returns SSE stream |
| GET | `/api/workspace` | - | Get current workspace info |
| POST | `/api/workspace` | - | Set workspace path |
| GET | `/api/workspaces` | - | List all workspaces under allowed roots |
| POST | `/api/workspace/new` | - | Create new workspace folder |
| GET | `/api/files` | - | Snapshot of workspace files |
| GET | `/api/files/stream` | - | SSE stream of workspace file changes |
| GET | `/api/health` | - | Health check: model, workspace, DB status |
| GET | `/api/history` | - | Job history (limit param) |
| GET | `/api/history/<job_id>` | - | Single job detail |

#### `generate()` — Main SSE Generator (inside `/api/chat`)

นี่คือ "หัวใจ" ของ backend flow:

```
1. สร้าง job_id ใน DB
2. capture workspace = get_workspace()  ← capture ONCE, ไม่เรียกซ้ำ (D3 risk)
3. เรียก _cleanup_old_temp()

4. if pending_temp_paths:
     if save_intent → handle_pm_save()
     if edit_intent (not discard) → บอก user ให้ save ก่อน
     if discard → ลบ temp files
     else → ลบ temp files + ดำเนินการต่อ

5. if pending_doc + pending_agent:
     if save_intent → handle_save()
     if discard_intent → ยกเลิก
     if edit_intent → handle_revise()
     else → ยกเลิกเอกสารเดิม ดำเนินการต่อ

6. Orchestrator.route() → agent_type, reason
7. AgentFactory.get_agent(agent_type)

8. if agent_type == 'pm':
     PMAgent.plan() → subtasks[]
     for each subtask:
       sub_agent.stream_response("[PM_SUBTASK]\n{task}")
       _write_temp(content) → temp_path
       yield pending_file SSE

   else:
     agent.run_with_tools(user_input, workspace, READ_ONLY_TOOLS)
     yield all SSE dicts

9. yield done SSE
```

---

### 4.2 core/shared.py

ไฟล์นี้เก็บ **global shared state** ทั้งหมดของ app

#### Constants

| Variable | ที่มา | ค่า default |
|----------|-------|------------|
| `OPENROUTER_API_KEY` | env `OPENROUTER_API_KEY` | (required) |
| `MODEL` | env `OPENROUTER_MODEL` | `anthropic/claude-sonnet-4-5` |
| `_DEFAULT_WORKSPACE` | env `WORKSPACE_PATH` | `<project_root>/workspace` |
| `_ALLOWED_ROOTS` | env `ALLOWED_WORKSPACE_ROOTS` | `[<project_root>]` |
| `TEMP_DIR` | hardcoded | `<project_root>/temp` |

#### Global State

```python
WORKSPACE_PATH     # str — current workspace (shared across all requests!)
_workspace_lock    # threading.Lock — protects WORKSPACE_PATH reads/writes
_ws_change_queues  # dict[workspace_path, list[Queue]] — event bus for SSE watchers
_ws_change_lock    # threading.Lock — protects _ws_change_queues
client             # OpenAI instance (configured for OpenRouter)
```

#### Functions

##### `get_workspace() -> str`
อ่าน `WORKSPACE_PATH` แบบ thread-safe (ใช้ lock)

##### `set_workspace(path: str) -> None`
ตั้งค่า `WORKSPACE_PATH` แบบ thread-safe

> **WARNING D3:** `WORKSPACE_PATH` เป็น **global ร่วมกันทุก session** ถ้า user A เปลี่ยน workspace และ user B กำลัง generate อยู่พร้อมกัน user B จะใช้ workspace ของ user A
> **Safe usage rule:** เรียก `get_workspace()` **ครั้งเดียวต้นของ request** แล้วส่งเป็น parameter ลงไป

##### `_notify_workspace_changed(workspace_path: str) -> None`
ส่ง `'changed'` เข้า queue ของทุก SSE client ที่ watch workspace นั้น
ทำให้ `/api/files/stream` push file list ใหม่ทันที

##### `get_model() -> str`, `get_client() -> OpenAI`
Getter functions (ไว้ใช้ใน agents)

---

### 4.3 core/orchestrator.py

#### Class: `Orchestrator`

รับ user message → ตัดสินใจว่าจะส่งให้ agent ไหน

##### `__init__()`
โหลด system prompt จาก `prompts/orchestrator.md`

##### `route(user_message, history=None) -> tuple[str, str]`

**Parameters:**
- `user_message`: ข้อความจาก user
- `history`: list ของ `{role, content}` (conversation context)

**Returns:** `(agent_type, reason)`
- `agent_type`: หนึ่งใน `'hr'`, `'accounting'`, `'manager'`, `'pm'`, `'chat'`
- `reason`: เหตุผลสั้นๆ ที่ LLM ตัดสินใจ (แสดงใน UI)

**How it works:**
1. เรียก LLM แบบ non-streaming พร้อม `response_format: json_object`
2. LLM return JSON: `{"agent": "hr", "reason": "..."}`
3. Parse JSON → return tuple
4. ถ้า JSON parse error → fallback `("chat", "Error parsing...")`

**Routing rules (จาก orchestrator.md):**

| Agent | เมื่อไหร่ |
|-------|---------|
| `hr` | สัญญาจ้าง, JD, นโยบาย HR, อีเมลพนักงาน |
| `accounting` | Invoice, รายงานการเงิน, งบประมาณ |
| `manager` | Feedback ทีม, Headcount Request, ขวัญกำลังใจ |
| `pm` | งานที่ต้องการ agents หลาย domain พร้อมกัน |
| `chat` | ทักทาย, คำถามทั่วไป, ไม่แน่ใจ (default fallback) |

---

### 4.4 core/utils.py

Utility functions ที่ใช้ทั่วทั้ง backend

##### `load_prompt(name: str) -> str`
โหลดไฟล์จาก `prompts/{name}.md`
- Raises `FileNotFoundError` ถ้าไม่พบไฟล์

##### `_web_search(query, max_results=5) -> str`
ค้นหาผ่าน DuckDuckGo (`ddgs` library)
- Timeout: `WEB_SEARCH_TIMEOUT` env (default 15 วิ)
- Return: Markdown string ของผลลัพธ์ พร้อม "ที่มา: URL"
- ถ้า error → return error message (ไม่ raise)

##### `extract_web_sources(result: str) -> list`
ดึง URL จาก result string ของ `_web_search`
- Parses `ที่มา: https://...` lines
- Return: `[{"url": ..., "domain": ...}, ...]`

##### `execute_tool(workspace, tool_name, tool_args) -> str`
**dispatcher** สำหรับ MCP tools ทั้งหมด:

```python
'create_file'  → fs_create_file(workspace, filename, content)
'read_file'    → fs_read_file(workspace, filename)
'update_file'  → fs_update_file(workspace, filename, content)
'delete_file'  → fs_delete_file(workspace, filename)
'list_files'   → fs_list_files(workspace) → formatted string
'web_search'   → _web_search(query, max_results)
unknown tool   → "❌ ไม่รู้จัก tool: {name}"
```

- FileNotFoundError, FileExistsError, ValueError → return `"❌ {str(e)}"`
- Exception อื่น → log + return `"❌ เกิดข้อผิดพลาด..."`

##### `format_sse(data: dict) -> str`
แปลง dict เป็น SSE string:
```
data: {"type": "text", "content": "..."}\n\n
```

---

### 4.5 core/agent_factory.py

#### Class: `AgentFactory`

**Thread-safe singleton cache** สำหรับ agent instances

```python
AgentFactory._agents = {}     # dict[str, BaseAgent]
AgentFactory._lock   = Lock() # double-checked locking
```

##### `get_agent(agent_type: str) -> BaseAgent`
- `agent_type`: `'hr'`, `'accounting'`, `'manager'`, `'pm'`, `'chat'`
- ถ้ายังไม่มีใน cache → สร้าง instance ใหม่ (lazy initialization)
- ถ้า agent_type ไม่รู้จัก → log warning + return ChatAgent

**Pattern:** double-checked locking — check without lock (fast path), then check with lock before create

> **Note:** Agent instances ถูก reuse ข้ามทุก request เนื่องจากเป็น stateless objects (system_prompt + client reference เท่านั้น ไม่มี per-request state)

---

### 4.6 agents/base_agent.py

#### Class: `BaseAgent`

Base class ที่ agent ทุกตัว inherit

##### `__init__(name, system_prompt)`
- `name`: ชื่อแสดงใน UI (เช่น "HR Agent")
- `system_prompt`: โหลดจาก prompts/ directory

##### `stream_response(message, history=None, max_tokens=8000)`
**Generator** — simple streaming ไม่มี tool calls

**Parameters:**
- `message`: user message
- `history`: list of `{role, content}` สำหรับ multi-turn context
- `max_tokens`: จำกัดความยาว output

**Yields:** text chunks (str) ทีละ delta

**Error handling:**
- `GeneratorExit` → re-raise (ให้ caller จัดการ)
- Exception อื่น → log + re-raise (caller ใน app.py จัดการ)

**ใช้ใน:**
- Chat Agent (สนทนาทั่วไป)
- PM subtasks (แต่ละ sub-agent)
- handle_revise (แก้ไขเอกสาร)

##### `run_with_tools(user_message, workspace, tools, history=None, max_tokens=8000, max_iterations=5)`
**Generator** — agentic loop พร้อม tool calls

**Parameters:**
- `user_message`: ข้อความ user
- `workspace`: path ของ workspace (ส่งเข้า execute_tool)
- `tools`: list ของ tool definitions (OpenAI format)
- `max_iterations`: ป้องกัน infinite loop (default 5)

**Yields:** dicts (ไม่ใช่ SSE string โดยตรง — app.py จะ wrap ด้วย format_sse)

**The Agentic Loop — step by step:**

```
for iteration in 0..max_iterations:

  1. เรียก LLM API (streaming=True) พร้อม tools
     - สะสม text chunks → text_streamed
     - สะสม tool_calls deltas → tool_calls_acc dict

  2. เช็ค finish_reason:
     - 'length' → log warning, yield status, ถ้าไม่มี tool_calls → return

  3. ตรวจ fake tool-call JSON ใน text_streamed:
     - ถ้าเจอ pattern {"request":"..."} หรือ {"tool":"..."} → strip ออก
     - yield text_replace event ให้ frontend แก้ข้อความที่แสดง

  4. ถ้าไม่มี tool_calls → return (จบ loop)

  5. สร้าง tool_calls_list (sorted by index)

  6. append assistant message พร้อม tool_calls ลง messages

  7. for each tool_call:
     - ตรวจ tool ใน allowed_names → ถ้าไม่ผ่าน yield error + return
     - parse JSON arguments
     - web_search rate limit: MAX_WEB_SEARCH_CALLS = 3
     - yield status (กำลังค้นหา / กำลังอ่าน / กำลังบันทึก)
     - execute_tool(workspace, tool_name, args)
     - append tool result ลง messages
     - yield tool_result หรือ web_search_sources

  8. ถ้า text_streamed มีค่า → return (ตอบแล้ว ไม่ต้อง loop ต่อ)

หลังจบ loop (I1 issue):
  yield status "ดำเนินการครบ N รอบแล้ว กรุณาลองใหม่"
```

**Known issues handled:**
- **I1:** loop exhausted — yield status message แทน silent fail
- **I2:** `finish_reason='length'` — log + yield warning status
- **I3:** fake tool-call JSON leak — strip ด้วย regex ทั้ง server และ client side

---

### 4.7 agents/ (each agent)

ทุก agent ยกเว้น PM เป็นเพียง wrapper เรียบง่ายมาก:

```python
class HRAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="HR Agent", system_prompt=load_prompt("hr_agent"))
```

| Agent | Class | name | Prompt file |
|-------|-------|------|------------|
| HR | `HRAgent` | "HR Agent" | `prompts/hr_agent.md` |
| Accounting | `AccountingAgent` | "Accounting Agent" | `prompts/accounting_agent.md` |
| Manager | `ManagerAgent` | "Manager Advisor" | `prompts/manager_agent.md` |
| Chat | `ChatAgent` | "Assistant" | `prompts/chat_agent.md` |

#### PMAgent (พิเศษ)

```python
class PMAgent(BaseAgent):
    def plan(self, user_message, history=None) -> list[dict]
```

##### `plan(user_message, history=None) -> list`
**Non-streaming** LLM call ที่ return JSON array:

```json
{
  "subtasks": [
    {"agent": "hr", "task": "รายละเอียด task ที่ self-contained"},
    {"agent": "accounting", "task": "..."}
  ]
}
```

- Valid agents: `{'hr', 'accounting', 'manager'}` — PM ห้ามอยู่ใน subtasks
- ถ้า JSON error → return `[]`
- ถ้า return `[]` → app.py yield error "PM Agent ไม่สามารถแบ่งงานได้"

**PM Agent ไม่มี tools** — ทำหน้าที่แค่ decompose งาน ไม่ generate เอกสารเอง

#### Tool Access Per Agent

| Agent | Tools available in run_with_tools |
|-------|----------------------------------|
| HR | `list_files`, `read_file`, `web_search` (READ_ONLY_TOOLS) |
| Accounting | `list_files`, `read_file`, `web_search` (READ_ONLY_TOOLS) |
| Manager | `list_files`, `read_file`, `web_search` (READ_ONLY_TOOLS) |
| Chat | `list_files`, `read_file`, `web_search` (READ_ONLY_TOOLS) |
| PM subtasks | ไม่มี — ใช้ `stream_response()` เท่านั้น |

> **เหตุผล:** Write tools (`create_file`, `update_file`, `delete_file`) ไม่ได้มอบให้ agents โดยตรง เพราะระบบต้องการให้ user confirm ก่อนบันทึก app.py เป็นผู้จัดการ save workflow ทั้งหมด

---

### 4.8 db.py

SQLite persistence layer พร้อม **graceful degradation** — ถ้า DB ล้มเหลว ระบบยังทำงานต่อได้ (แค่ไม่มี history)

#### Database Schema

**Table: `jobs`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID v4 |
| `created_at` | TEXT | ISO 8601 UTC timestamp |
| `session_id` | TEXT | browser session UUID (nullable) |
| `user_input` | TEXT | ข้อความที่ user พิมพ์ |
| `agent` | TEXT | agent ที่ถูกเลือก (nullable — set หลัง routing) |
| `reason` | TEXT | เหตุผลจาก Orchestrator |
| `status` | TEXT | `pending`, `completed`, `error`, `discarded` |
| `output_text` | TEXT | AI output ทั้งหมด (nullable) |

**Table: `saved_files`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID v4 |
| `job_id` | TEXT FK | references jobs.id |
| `created_at` | TEXT | ISO 8601 UTC |
| `filename` | TEXT | ชื่อไฟล์ที่บันทึก |
| `agent` | TEXT | agent ที่สร้างไฟล์ |
| `size_bytes` | INTEGER | ขนาดไฟล์ |

**Indexes:**
- `idx_jobs_created` on `jobs(created_at DESC)`
- `idx_files_job_id` on `saved_files(job_id)`

#### Functions

| Function | Description |
|----------|-------------|
| `init_db()` | สร้าง tables, integrity check, ทำความสะอาด zombie jobs (pending > 1 ชั่วโมง) |
| `create_job(user_input, session_id)` | INSERT job → return job_id หรือ None |
| `update_job_agent(job_id, agent, reason)` | อัปเดตหลัง Orchestrator routing |
| `complete_job(job_id, output_text)` | status = 'completed' |
| `fail_job(job_id)` | status = 'error' |
| `discard_job(job_id)` | status = 'discarded' |
| `record_file(job_id, filename, agent, size_bytes)` | INSERT saved_files row |
| `get_history(limit=50)` | jobs + files (JOIN) เรียงตาม created_at DESC |
| `get_job(job_id)` | single job + files |
| `db_status()` | `{available, path}` สำหรับ health endpoint |

**Connection settings:**
- WAL journal mode (concurrent reads ขณะ write)
- `timeout=5` seconds (busy wait)
- `check_same_thread=False` (Flask threaded mode)
- `PRAGMA foreign_keys=ON`

**Corruption recovery:** `_handle_corrupt_db()` rename ไฟล์ `.broken_{timestamp}` แล้ว set `DB_AVAILABLE=False`

---

### 4.9 mcp_server.py

มี 2 layers:

**Layer A: Core Python functions** (import โดย app.py)
```python
fs_list_files(workspace)              # list files → [{"name","size","modified"}]
fs_create_file(workspace, fn, content) # สร้างไฟล์ใหม่ (error ถ้ามีแล้ว)
fs_read_file(workspace, fn)           # อ่านไฟล์
fs_update_file(workspace, fn, content) # เขียนทับ (error ถ้าไม่มี)
fs_delete_file(workspace, fn)         # ลบไฟล์
```

**Layer B: FastMCP server** (รัน standalone ด้วย `python mcp_server.py`)
- Wraps Layer A ด้วย `@mcp.tool()` decorators
- ใช้ workspace จาก env `WORKSPACE_PATH`
- ถ้าไม่ได้ติดตั้ง `mcp` package → import error ถูก silently catch

#### Security: `_validate_path(workspace, filename) -> str`
ป้องกัน **path traversal attack**:
```python
target = Path(workspace_abs, filename).resolve()
if commonpath([workspace_abs, target]) != workspace_abs:
    raise ValueError("ไม่อนุญาต: อยู่นอก workspace")
```
- ตัวอย่าง attack ที่ถูกบล็อก: `filename = "../../etc/passwd"`

**Error conventions:**
- ไฟล์มีแล้วและ create → `FileExistsError`
- ไม่พบไฟล์ → `FileNotFoundError`
- path traversal → `ValueError`
- ทุก error message เป็นภาษาไทย

---

### 4.10 converter.py

แปลง Markdown text เป็น format ต่างๆ

#### Public API

```python
SUPPORTED_FORMATS = {'md', 'txt', 'docx', 'xlsx', 'pdf'}

convert(text: str, fmt: str) -> bytes
```

#### Per-format behavior

| Format | Function | Dependencies | Notes |
|--------|----------|-------------|-------|
| `.md` | `to_md()` | - | `text.encode('utf-8')` เท่านั้น |
| `.txt` | `to_txt()` | - | `text.encode('utf-8')` เท่านั้น |
| `.docx` | `to_docx()` | python-docx | Parse markdown line-by-line, Thai font: TH Sarabun New |
| `.xlsx` | `to_xlsx()` | openpyxl | ดึงตาราง markdown แรกที่พบ; ถ้าไม่มีตาราง → ใส่ข้อความทั้งหมดใน A1 |
| `.pdf` | `to_pdf()` | weasyprint, markdown | Markdown → HTML → PDF, Thai fonts: Norasi/TH Sarabun New/Garuda |

**DOCX parsing (line-by-line):**
- `# ` → `add_heading(level=1)`
- `## ` → `add_heading(level=2)`
- `### ` → `add_heading(level=3)`
- `| ... |` → collect consecutive table lines → `add_table()`
- `- text` or `* text` → List Bullet style
- `---` → horizontal rule (50× `─`)
- inline `**bold**` → bold run ผ่าน `_add_inline_runs()`

---

## 5. SSE Event Reference

SSE format: `data: {JSON}\n\n`

ทุก event เป็น JSON object มี field `type` บังคับ

| `type` | Payload fields | Frontend action |
|--------|---------------|-----------------|
| `status` | `message: str` | แสดงใน `#status` element |
| `agent` | `agent: str, reason: str, task?: str` | อัปเดต agent badge; สร้าง PM card ถ้า `wasPMTask` |
| `pm_plan` | `subtasks: [{agent,task}]` | แสดง PM plan breakdown ก่อน content |
| `text` | `content: str` | append ลง `currentOutputEl.textContent` (live streaming) |
| `text_replace` | `content: str` | replace ทั้ง `outputText` + DOM (หลัง strip fake tool-call) |
| `tool_result` | `tool: str, result: str` | แสดง tool result badge ก่อน output area |
| `web_search_sources` | `query: str, sources: [{url,domain}]` | แสดง source pills ก่อน output area |
| `pending_file` | `temp_path: str, filename: str, agent: str` | เพิ่ม path ลง `pendingTempPaths[]` |
| `subtask_done` | `agent: str, index: int, total: int` | render markdown สำหรับ subtask นี้, reset `outputText` |
| `save_failed` | `message: str` | แสดง error, restore pending state |
| `error` | `message: str` | แสดง error inline, reset state |
| `done` | (ไม่มี extra fields) | render markdown สุดท้าย, re-enable send button, set pending state |
| `heartbeat` | (ไม่มี extra fields) | ไม่ทำอะไร (keepalive สำหรับ files/stream) |
| `files` | `files: [{name,size,modified}], workspace: str` | อัปเดต file list ใน sidebar |

---

## 6. Frontend State Variables (index.html)

JavaScript ทั้งหมดอยู่ใน `<script>` block ท้าย HTML ไม่มี external JS module

### Global State Variables

| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
| `pendingDoc` | string | `''` | เนื้อหาเอกสารที่ agent สร้างและรอ user confirm |
| `pendingAgent` | string | `''` | ชื่อ agent ที่สร้าง `pendingDoc` |
| `pendingFormat` | string | `'md'` | format ที่ user เลือกสำหรับบันทึก (ถูก lock ตอน generation) |
| `pendingTempPaths` | array | `[]` | absolute paths ของ temp files จาก PM subtasks |
| `pendingFileAgents` | array | `[]` | agent type ต่อ temp file (parallel array กับ pendingTempPaths) |
| `isPendingConfirmation` | boolean | `false` | true = มีเอกสารรอ confirm (แสดง hint ใน input bar) |
| `wasPMTask` | boolean | `false` | true = current response เป็น PM flow (render PM cards) |
| `currentPmCard` | Element/null | `null` | DOM element ของ PM card ปัจจุบัน |
| `lastAgent` | string | `''` | agent_type ของ event ล่าสุด (ใช้ set pendingAgent ตอน done) |
| `queuedMessage` | string | `''` | task ที่ถูก queue หลังจาก user เลือก "save first" ใน modal |
| `pendingFileFormats` | array/null | `null` | formats ที่ user เลือกจาก file format modal (PM save) |
| `conversationHistory` | array | `[]` | `[{role, content}]` — ส่งไป backend ทุก request |
| `userScrolledUp` | boolean | `false` | หยุด auto-scroll ถ้า user scroll ขึ้นไปอ่าน |

### Key Frontend Functions

| Function | Description |
|----------|-------------|
| `sendMessage(overrideMessage?)` | Main function — intercepts modal flows, calls `/api/chat`, reads SSE stream |
| `startFileStream()` | เปิด EventSource `/api/files/stream` และ handle `files` events |
| `renderFileList(files, workspace)` | อัปเดต sidebar file list DOM |
| `fillInput(text)` | ใส่ข้อความลง textarea (ใช้กับ nav-item shortcuts) |
| `cancelPending()` | ล้าง pending state ทั้งหมด (ไม่ส่ง API) |
| `copyOutput()` | คัดลอก text จาก `.output-area` ล่าสุดลง clipboard |
| `toggleTheme()` | toggle dark/light mode และ save ลง localStorage |
| `changeWorkspace()` | เปิด workspace picker modal, fetch `/api/workspaces` |
| `_applyWorkspace(path)` | POST `/api/workspace`, reset conversation history, restart file stream |
| `_createWorkspaceFolder()` | POST `/api/workspace/new` |
| `_showFileFormatModal(msg)` | แสดง format selector modal สำหรับ PM multi-file save |
| `_showSingleFileFormatModal(msg)` | แสดง format selector modal สำหรับ single-agent save |
| `_showCancelConfirmModal(msg, count)` | confirmation modal ก่อน discard PM files |
| `_showPendingModal(newTask)` | modal ถาม user ว่าจะ save ก่อน / skip / cancel เมื่อมีงานใหม่มา |
| `_isSaveIntentJS(msg)` | client-side save detection (subset ของ backend) |
| `_isCancelIntentJS(msg)` | client-side cancel detection |
| `_isNewTask(msg)` | true ถ้า message ไม่ใช่ save/cancel/edit keyword |
| `_extractFormatFromMessage(msg)` | detect format จากคำใน message เช่น "pdf", "excel" |
| `_renderMarkdown(el, text)` | `marked.parse()` + `_sanitizeHtml()` → innerHTML |
| `_sanitizeHtml(html)` | ลบ script/iframe tags + on* attributes ป้องกัน XSS |
| `_renderPmPlan(div, subtasks)` | สร้าง PM plan breakdown DOM |
| `_renderToolResult(div, tool, result)` | สร้าง tool result badge DOM |
| `_setAgentBadge(badge, info, reason)` | อัปเดต agent badge ใน sidebar |
| `_setInlineError(el, message)` | แสดง error inline ใน output area |
| `_updateInputHint(isPending, fileCount)` | อัปเดต input hint text และ cancel button |
| `_scrollToBottom()` | scroll output ลงล่าง (เฉพาะถ้า `!userScrolledUp`) |
| `_formatBytes(b)` | แปลง bytes → "1.2KB" |
| `_getSessionId()` | get/create session UUID จาก localStorage |

### Modals

| Modal ID | แสดงเมื่อ |
|----------|---------|
| `pendingModal` | user พิมพ์งานใหม่ขณะมี pending doc |
| `fileFormatModal` | save PM files หรือ save single-agent file (เลือก format) |
| `cancelConfirmModal` | user พิมพ์ "ยกเลิก" ขณะมี PM pending files |
| `workspaceModal` | user คลิก workspace selector ใน navbar |

---

## 7. Configuration Reference

ตัวแปรทั้งหมดมาจากไฟล์ `.env` (โหลดด้วย `python-dotenv`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | **(required)** | API key จาก openrouter.ai |
| `OPENROUTER_MODEL` | `anthropic/claude-sonnet-4-5` | Model ที่ใช้ — เปลี่ยนได้โดยไม่แก้ code |
| `OPENROUTER_TIMEOUT` | `60` | Timeout สำหรับ API requests (วินาที) |
| `WORKSPACE_PATH` | `./workspace` | Default workspace directory |
| `ALLOWED_WORKSPACE_ROOTS` | `<project_root>` | Comma-separated paths ที่ user เปลี่ยน workspace ได้ |
| `MAX_PENDING_DOC_BYTES` | `204800` (200KB) | จำกัดขนาด pending_doc จาก frontend |
| `WEB_SEARCH_TIMEOUT` | `15` | Timeout สำหรับ DuckDuckGo search (วินาที) |
| `CHAT_RATE_LIMIT` | `10 per minute` | Rate limit สำหรับ `/api/chat` (flask-limiter syntax) |
| `RATELIMIT_STORAGE_URI` | `memory://` | Storage backend สำหรับ rate limiter (Redis สำหรับ multi-process) |
| `FLASK_DEBUG` | `0` | เปิด Flask debug mode (อย่าใช้ใน production) |
| `FLASK_HOST` | `0.0.0.0` | Bind address |
| `FLASK_PORT` | `5000` | Port (ใช้กับ `app.run()` เท่านั้น — gunicorn มี config แยก) |
| `GUNICORN_WORKERS` | `2` | จำนวน worker processes |
| `GUNICORN_CONNECTIONS` | `50` | Max concurrent SSE connections ต่อ worker |
| `GUNICORN_TIMEOUT` | `120` | Worker timeout (ต้องมากกว่า OPENROUTER_TIMEOUT) |
| `GUNICORN_LOG_LEVEL` | `info` | Log level: debug/info/warning/error |

---

## 8. Common Flows (step-by-step)

### 8.1 Normal Chat Flow

```
User: "สวัสดี"

1. [Browser] sendMessage("สวัสดี")
   → POST /api/chat { message: "สวัสดี", conversation_history: [] }

2. [Flask] generate()
   → ไม่มี pending state
   → yield SSE: {type: "status", message: "กำลังวิเคราะห์งาน..."}

3. [Orchestrator.route()] → {agent: "chat", reason: "บทสนทนาทั่วไป"}
   → yield SSE: {type: "agent", agent: "chat", reason: "..."}

4. [ChatAgent.run_with_tools()]
   → LLM streaming (may call list_files/web_search)
   → yield SSE: {type: "text", content: "สวัสดีครับ..."} (หลายครั้ง)

5. → yield SSE: {type: "done"}

6. [Browser] render markdown, enable send button
   → lastAgent = "chat" → ไม่ set pendingConfirmation (chat ไม่มีไฟล์)
```

### 8.2 Document Generation Flow (single agent)

```
User: "ร่างสัญญาจ้างพนักงานชื่อ สมชาย ตำแหน่ง นักบัญชี เงินเดือน 35,000"

1. POST /api/chat { message: "..." }

2. Orchestrator → {agent: "hr"}
   yield: {type: "agent", agent: "hr", reason: "สัญญาจ้างงาน"}

3. HRAgent.run_with_tools()
   - iteration 0: LLM call with READ_ONLY_TOOLS
     - อาจเรียก list_files ก่อนดูว่ามีไฟล์เดิมไหม
     - yield tool_result
     - สร้างเนื้อหาสัญญาจ้าง
     - yield text (streaming)
   - ไม่มี tool_calls ที่ 2 → return

4. yield: {type: "done"}

5. [Browser] outputText = สัญญาจ้างทั้งหมด
   → render markdown
   → pendingDoc = outputText, pendingAgent = "hr"
   → isPendingConfirmation = true
   → _updateInputHint(true, 0)  ← hint เปลี่ยนเป็น "พิมพ์ บันทึก"

--- User พิมพ์ "บันทึก" ---

6. sendMessage("บันทึก")
   → pendingDoc + pendingAgent set
   → _isSaveIntentJS("บันทึก") = true
   → _showSingleFileFormatModal("บันทึก")  ← modal เลือก format

7. User เลือก .docx → click "บันทึกทั้งหมด"
   → pendingFormat = "docx"
   → sendMessage("บันทึก") [ครั้งที่ 2 พร้อม format]

8. POST /api/chat { message: "บันทึก", pending_doc: "...", pending_agent: "hr",
                    output_format: "docx" }

9. [Flask] _is_save_intent("บันทึก") = true
   → handle_save(pending_doc, "hr", workspace, job_id, "docx")
     - converter.convert(content, "docx") → bytes
     - เขียน .docx ไป workspace/
     - db.record_file()
     - _notify_workspace_changed()
   yield: {type: "text", content: "✅ บันทึก hr_...docx เรียบร้อย"}
   yield: {type: "tool_result", ...}
   yield: {type: "done"}

10. [Browser] sidebar file list อัปเดต (via files/stream SSE)
```

### 8.3 PM Multi-Agent Flow

```
User: "สร้างเอกสาร onboarding พนักงานใหม่: HR Contract + Invoice ค่าบริการ"

1. POST /api/chat { message: "..." }

2. Orchestrator → {agent: "pm", reason: "งานข้ามหลาย domain"}
   yield: {type: "agent", agent: "pm"}

3. PMAgent.plan() → non-streaming LLM call
   → subtasks = [
       {agent: "hr", task: "ร่างสัญญาจ้าง..."},
       {agent: "accounting", task: "สร้าง Invoice..."}
     ]
   yield: {type: "pm_plan", subtasks: [...]}
   [Browser] แสดง PM breakdown ก่อน content

4. Loop subtask 0 (HR):
   yield: {type: "agent", agent: "hr", reason: "Subtask 1/2", task: "ร่างสัญญาจ้าง..."}
   [Browser] สร้าง pm-agent-card.card-hr

   HRAgent.stream_response("[PM_SUBTASK]\nร่างสัญญาจ้าง...")
   yield: {type: "text", content: "..."} × N

   _write_temp(content, "hr") → temp/hr_..._timestamp.md
   yield: {type: "pending_file", temp_path: "temp/...", filename: "...", agent: "hr"}
   [Browser] pendingTempPaths.push(temp_path)

   yield: {type: "subtask_done", agent: "hr", index: 0, total: 2}
   [Browser] render markdown สำหรับ HR card

5. Loop subtask 1 (Accounting):
   (เหมือนกัน — สร้าง accounting card, เขียน temp file ที่ 2)

6. yield: {type: "done"}
   [Browser] isPendingConfirmation = true
   _updateInputHint(true, 2)  ← "พิมพ์ บันทึก เพื่อบันทึก 2 ไฟล์"

--- User พิมพ์ "บันทึก" ---

7. sendMessage("บันทึก")
   → pendingTempPaths.length > 0
   → _isSaveIntentJS = true
   → _showFileFormatModal("บันทึก")  ← modal แสดง 2 rows สำหรับ 2 ไฟล์

8. User เลือก format ต่อไฟล์ → click "บันทึกทั้งหมด"
   → pendingFileFormats = ["md", "pdf"]
   → sendMessage("บันทึก")

9. POST /api/chat { message: "บันทึก",
                    pending_temp_paths: ["temp/hr_...", "temp/acc_..."],
                    agent_types: ["hr", "accounting"],
                    output_formats: ["md", "pdf"] }

10. [Flask] pending_temp_paths + save_intent
    → handle_pm_save()
      - ย้าย/convert แต่ละ temp file ไป workspace/
      - db.record_file() × 2
      - _notify_workspace_changed() × 2
    yield: {type: "tool_result"} × 2
    yield: {type: "text", content: "✅ บันทึก 2 ไฟล์เรียบร้อย\n..."}
    yield: {type: "done"}
```

### 8.4 Edit Pending Document Flow

```
[User มี pendingDoc = สัญญาจ้าง]

User: "เพิ่มรายละเอียดเรื่องสวัสดิการประกันสุขภาพ"

1. sendMessage("เพิ่ม...")
   → isPendingConfirmation = true
   → _isNewTask? — มี keyword "เพิ่ม" ซึ่งเป็น edit keyword
   → ไม่ show pending modal

2. POST /api/chat { message: "เพิ่ม...", pending_doc: "...", pending_agent: "hr" }

3. [Flask] _is_edit_intent("เพิ่ม") = true
   → handle_revise(pending_doc, "hr", "เพิ่มรายละเอียด...", history)
     - revise_message = "แก้ไขเอกสาร...\nคำสั่ง: เพิ่ม...\nเอกสารเดิม: {doc}"
     - HRAgent.stream_response(revise_message)
     - yield text chunks

4. yield: {type: "done"}

5. [Browser] pendingDoc = new content (updated)
   isPendingConfirmation = true (ยังรอ save)
```

---

## 9. Known Risks & Constraints

### D3 — Workspace Global State Risk (สำคัญมาก)

**ปัญหา:** `WORKSPACE_PATH` ใน `core/shared.py` เป็น process-level global variable ที่แชร์ระหว่างทุก request พร้อมกัน

```python
# ❌ อันตราย — อาจได้ workspace ที่ user อื่นเปลี่ยนไปแล้ว
def generate():
    for i in range(10):
        workspace = get_workspace()  # เรียกซ้ำใน loop!
        ...

# ✅ ถูกต้อง — capture ครั้งเดียวต้นของ request
def generate():
    workspace = get_workspace()  # capture once
    for i in range(10):
        do_something(workspace)  # pass as parameter
```

**Mitigation ปัจจุบัน:** code ใน `generate()` มี comment เตือนและ capture ครั้งเดียว

**แก้ไขระยะยาว:** เปลี่ยนเป็น per-session workspace dict:
```python
_workspaces: dict[str, str] = {}  # session_id → path
```

### D1 — OpenRouter Single Point of Failure

ระบบพึ่งพา OpenRouter API 100% ไม่มี fallback:
- ถ้า OpenRouter down → ทุก feature หยุดทำงาน
- ถ้า rate limit จาก OpenRouter → requests fail
- ไม่มี retry mechanism ในปัจจุบัน

**Mitigation:** แสดง error ที่ชัดเจนใน UI, rate limit จาก flask-limiter ช่วยลด load ก่อนถึง API

### I1 — run_with_tools Loop Exhaustion

ถ้า agent เรียก tools ครบ `max_iterations` (5 รอบ) โดยไม่มี final text response:
- ใน v0.15+ จะ yield status message แจ้ง user
- ก่อนหน้านี้: silent return (user เห็นแค่ tool results ไม่มี summary)

### I2 — Truncated Response (finish_reason='length')

ถ้า max_tokens ถูกตัดกลางกรณีที่ LLM กำลัง generate:
- ถ้ามี tool calls ค้างอยู่ → loop ต่อ (อาจได้ partial tool args)
- ถ้าไม่มี tool calls → yield status + return

### I3 — Fake Tool-Call JSON Leak

บาง models output tool call JSON เป็น plain text แทนที่จะใช้ structured `tool_calls` channel:
```json
{"request": "web_search", "query": "..."}
```

**Mitigation:**
- Server: `_FAKE_TOOL_CALL_RE` regex strip + yield `text_replace` event
- Client: real-time regex strip ระหว่าง text streaming

### Rate Limiting

- Default: 10 requests/minute ต่อ IP
- Storage default: `memory://` — **reset เมื่อ Flask restart** และ **ไม่ sync ระหว่าง workers**
- Production multi-process: ต้องเปลี่ยน `RATELIMIT_STORAGE_URI=redis://localhost:6379/0`

### XLSX Export Limitation

`to_xlsx()` ดึง **ตาราง markdown แรกเท่านั้น** ถ้า document มีหลายตาราง ตารางที่ 2+ จะหาย ถ้าไม่มีตาราง content ทั้งหมดจะถูกใส่ใน cell A1 เดียว

### Conversation History Truncation

Frontend ส่ง history ไป backend แค่ `MAX_HISTORY_TURNS * 2 = 20 messages` และ backend จำกัดแต่ละ message ที่ 3,000 ตัวอักษร เอกสารยาวมากๆ ใน history จะถูกตัด

### PDF Export (WeasyPrint)

WeasyPrint log output verbose มาก (fontTools) — suppressed ด้วย:
```python
logging.getLogger('fontTools').setLevel(logging.ERROR)
logging.getLogger('weasyprint').setLevel(logging.WARNING)
```
ต้องการ system Thai fonts (Norasi, Garuda, Loma) ติดตั้งใน OS สำหรับ PDF ภาษาไทยที่สวยงาม

---

*เอกสารนี้ generate จากการอ่าน source code โดยตรง หากโค้ดเปลี่ยนแปลง กรุณาอัปเดตเอกสารนี้ด้วย*
