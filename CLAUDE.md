# AI POC — Internal AI Assistant

## โปรเจกต์นี้คืออะไร
Flask + OpenRouter API สำหรับ demo ต่อหัวหน้า
Multi-agent: Orchestrator → HR Agent / Accounting Agent / Manager Advisor
Output: เอกสารภาษาไทย (สัญญาจ้าง, invoice, JD, คำแนะนำการบริหารทีม)

## เอกสารสำคัญ — อ่านก่อนทำงานทุกครั้ง
- `docs/poc-plan.md`     — แผน POC 2 คืน พร้อม code และ demo script
- `docs/project-plan.md` — แผนการพัฒนาทั้งหมด Phase 0-4

## Stack
- Python 3.11 + Flask + flask-cors
- OpenAI SDK → OpenRouter (`https://openrouter.ai/api/v1`)
- SSE สำหรับ streaming response (`client.chat.completions.create(stream=True)`)
- index.html ไฟล์เดียว ไม่มี framework — dark mode default, toggle light/dark ได้

## โครงสร้างไฟล์
- app.py          — Flask server + Orchestrator + PM Agent + Agentic loop
- mcp_server.py   — MCP Filesystem Server (FastMCP) + 5 tools (Layer A/B)
- index.html      — Web UI (dark/light toggle, Enter ส่ง, Shift+Enter ขึ้นบรรทัดใหม่)
- .env            — `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `WORKSPACE_PATH` (ห้าม commit)
- .env.example    — template สำหรับ setup ใหม่
- requirements.txt — flask, flask-cors, openai, python-dotenv, mcp, watchdog
- workspace/       — workspace directory สำหรับ agent สร้างไฟล์ (gitignored ยกเว้น .gitkeep)
- temp/            — staging area สำหรับไฟล์ที่รอ confirm ก่อน move ไป workspace (gitignored ยกเว้น .gitkeep)
- test_cases.py   — ทดสอบ 5 use cases อัตโนมัติ (`PYTHONUTF8=1 python test_cases.py`)
- docs/           — project-plan.md, poc-plan.md
- .claude/agents/ — subagents ทั้งหมด

## Known Issues & Quirks
- **Reasoning models** (เช่น minimax/minimax-m2.7) ใช้ token ไปกับ internal thinking ก่อน — Orchestrator ต้องใช้ `max_tokens=1024` ขึ้นไป ไม่เช่นนั้น `content` จะเป็น `None`
- **Windows terminal** ต้อง prefix ด้วย `PYTHONUTF8=1` เมื่อรัน script ที่มีภาษาไทย
- model name ที่แสดงใน sidebar ดึงจาก `/api/health` endpoint ตอนโหลดหน้า (ไม่ได้ hardcode ใน HTML)

## Version Management

Version แสดงใน `index.html` บรรทัด `<div class="version">INTERNAL POC — vX.X.X</div>`

รูปแบบ: **v0.MINOR.PATCH**

| การเปลี่ยนแปลง | bump | ตัวอย่าง |
|---|---|---|
| เพิ่ม Agent ใหม่, ฟีเจอร์หลักใหม่ (route ใหม่, capability ใหม่) | Minor | v0.2.x → v0.3.0 |
| Bug fix, UI tweak, prompt update, doc update | Patch | v0.2.0 → v0.2.1 |

กฎ:
- **ทุก commit ต้อง bump version** ใน index.html พร้อมกัน
- **ทุก commit ต้องเพิ่ม entry ใน CHANGELOG.md** ระบุ version, วันที่, ประเภท, รายละเอียด
- เมื่อ bump Minor ให้ reset Patch เป็น 0 เสมอ (v0.2.3 → v0.3.0)
- Version ปัจจุบัน: **v0.4.9**

ประวัติ:
- v0.1.0 — initial POC (HR + Accounting agents, SSE streaming)
- v0.2.0 — Manager Advisor agent + timer counter + copy button
- v0.2.1 — fix Manager badge label/color, update sidebar agent list
- v0.2.2 — adopt semantic versioning scheme
- v0.2.3 — PROJECT_SUMMARY.md (AI context document)
- v0.3.0 — UI redesign "The Silent Concierge" (Navbar + Sidebar redesign, dark/light tokens, Material Symbols)
- v0.3.1 — Markdown rendering (marked.js) + status-row solid background fix
- v0.3.2 — auto-resize textarea (1–5 บรรทัด)
- v0.3.3 — input area redesign: button absolute inside container (ChatGPT style)
- v0.3.4 — agent badge reserved space + idle state
- v0.3.5 — nav-items → pill chips, dark mode สว่างขึ้น
- v0.3.6 — typing indicator (3 bouncing dots) ก่อน streaming เริ่ม
- v0.3.7 — fix accent line สูงพอดี bubble ระหว่าง typing state
- v0.3.8 — fix "tokens"→"ตัวอักษร" + typing indicator ค้างเมื่อ error
- v0.3.9 — chat bubble UI: user bubble ขวา, AI ซ้าย, ประวัติสะสม
- v0.4.0 — PM Agent + MCP Filesystem (workspace selector, real-time file panel, agentic tool-calling loop)
- v0.4.1 — Confirmation flow: AI generates → asks to edit or save → user confirms before file write
- v0.4.2 — fix PM Agent JSON parse robustness + sidebar badge overflow
- v0.4.3 — temp staging flow: PM subtasks stream full content → temp dir → confirm → move to workspace
- v0.4.4 — fix PM Agent max_tokens 1024→6000 (subtask JSON truncation) + finish_reason logging
- v0.4.5 — fix pending state hijack: ✕ ยกเลิก button + _is_discard_intent() backend safety net
- v0.4.6 — fix fall-through routing: งานใหม่ขณะ pending → ยกเลิกเดิม + ส่งงานใหม่ไป Orchestrator
- v0.4.7 — fix new-task-vs-edit: _is_edit_intent() แยก edit instruction ออกจากงานใหม่ ป้องกัน handle_revise() ถูกเรียกผิด
- v0.4.8 — harden runtime default: ปิด Flask debug mode สำหรับการรันปกติ และเปิดได้ผ่าน FLASK_DEBUG
- v0.4.9 — harden workspace switching: จำกัด runtime workspace ให้อยู่ภายใต้ project root

## Rules ที่ต้องทำตามเสมอ
- ภาษาไทยใน UI และ system prompts ทั้งหมด
- ทุก agent output ต้องมี disclaimer ว่าเป็น draft
- Error messages เป็นภาษาไทยที่ user เข้าใจ ไม่ใช่ technical
- ห้าม hardcode API key ใน code เด็ดขาด
- ก่อนเริ่มงานใหม่ทุกครั้ง อ่าน docs/poc-plan.md ก่อน
- **ทุกครั้งที่มีการเปลี่ยนแปลงโค้ดที่อาจส่งผลต่อเอกสาร ให้อัปเดตเอกสารที่เกี่ยวข้องทันที** ดูตารางด้านล่าง

### เอกสารที่ต้องอัปเดตเมื่อโค้ดเปลี่ยน

| เมื่อเปลี่ยน | อัปเดตเอกสารเหล่านี้ |
|---|---|
| version ใน index.html | CLAUDE.md (Version ปัจจุบัน + ประวัติ), CHANGELOG.md, PROJECT_SUMMARY.md (version + history table), docs/poc-plan.md (file tree), docs/project-plan.md (POC version), DEMO-READINESS-REPORT.md |
| UI feature ใหม่ (index.html) | PROJECT_SUMMARY.md (UI Architecture), DEMO-READINESS-REPORT.md (UI FEATURES), docs/poc-plan.md (progress list) |
| Agent ใหม่ หรือ agent logic เปลี่ยน (app.py) | PROJECT_SUMMARY.md (Agents table), docs/poc-plan.md (Agent table + progress), DEMO-READINESS-REPORT.md (Agent Routing Status) |
| โครงสร้างไฟล์เปลี่ยน | PROJECT_SUMMARY.md (โครงสร้างไฟล์), CLAUDE.md (โครงสร้างไฟล์), docs/poc-plan.md (file tree) |
| Demo use cases เปลี่ยน | PROJECT_SUMMARY.md (Demo Use Cases), docs/poc-plan.md (session log), DEMO-READINESS-REPORT.md (USE CASES STATUS), backup/demo-inputs.txt |

## Agent Workflow Rules — Follow Automatically

These rules apply without needing to be asked:

### After writing or editing any .py file
→ ALWAYS run python-reviewer before considering done

### After any error or exception appears  
→ ALWAYS run debug-assistant immediately

### After generating any Thai document output
→ ALWAYS run thai-doc-checker

### After writing or editing index.html
→ Run frontend-developer to verify
→ Then run ui-ux-reviewer to validate UX

### Before demo or dry-run
→ Run security-checker first
→ Then run demo-preparer for full checklist

### After any code change affecting documentation
→ Update related docs immediately (see table in "Rules ที่ต้องทำตามเสมอ")
→ Do NOT wait until end of session — update inline as part of the same change

### At end of each work session
→ Run project-documenter to update docs/poc-plan.md
