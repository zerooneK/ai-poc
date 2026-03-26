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
- app.py                  — Flask server + Orchestrator + PM Agent + Agentic loop + DB integration
- db.py                   — SQLite persistence layer (jobs, saved_files) — graceful degradation
- converter.py            — Multi-format export (.txt/.docx/.xlsx/.pdf) — deferred imports, no startup crash
- mcp_server.py           — MCP Filesystem Server (FastMCP) + 5 tools (Layer A/B)
- index.html              — Web UI (dark/light toggle, Enter ส่ง, Shift+Enter ขึ้นบรรทัดใหม่)
- history.html            — Standalone job history viewer page (Flask route /history)
- .env                    — `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `WORKSPACE_PATH` (ห้าม commit)
- .env.example            — template สำหรับ setup ใหม่
- requirements.txt        — flask, flask-cors, openai, python-dotenv, mcp, watchdog, python-docx, openpyxl, weasyprint, markdown
- setup.sh                — auto-install script: venv, pip deps, WeasyPrint system libs, Thai fonts, verify step
- start.sh                — run script: activate venv + flask run host=0.0.0.0 (WSL-compatible)
- workspace/              — workspace directory สำหรับ agent สร้างไฟล์ (gitignored ยกเว้น .gitkeep)
- temp/                   — staging area สำหรับไฟล์ที่รอ confirm ก่อน move ไป workspace (gitignored ยกเว้น .gitkeep)
- data/                   — SQLite database directory (gitignored ยกเว้น .gitkeep) — assistant.db สร้างอัตโนมัติ
- test_cases.py           — ทดสอบ 5 use cases อัตโนมัติ (`PYTHONUTF8=1 python test_cases.py`)
- smoke_test_phase0.py    — Phase 0 smoke test (5 checks, urllib-based, Thai confirmation safe on Windows)
- quick-demo-check.py     — Full validation script (7 checks รวม health)
- PRE-DEMO-CHECKLIST.md   — Checklist 30 นาทีก่อน demo
- docs/                   — project-plan.md, poc-plan.md, phase-0-safe-execution-plan.md
- backup/                 — demo-inputs.txt, demo-script.md, screenshots/
- .claude/agents/         — subagents ทั้งหมด

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
- Version ปัจจุบัน: **v0.11.0**

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
- v0.4.10 — harden save confirmation flow: save fail แล้วไม่หลอกว่าสำเร็จ และไม่ทำ pending state หาย
- v0.4.11 — harden frontend rendering: sanitize markdown และลดการใช้ innerHTML กับข้อมูลจาก server/LLM
- v0.4.12 — smoke test harness hardening: เพิ่ม `smoke_test_phase0.py`, กัน false alarm จาก Windows shell encoding, และเพิ่ม retry/timeout diagnostics
- v0.4.13 — fix 5A: เพิ่ม `done` event ใน outer except blocks ป้องกัน frontend ค้างเมื่อเกิด error
- v0.4.14 — fix 5B: PM subtask loop break เมื่อ subtask error ป้องกัน loop วิ่งต่อหลังพัง
- v0.4.15 — fix 5C: นำ 'งานใหม่'/'เริ่มใหม่' ออกจาก _DISCARD_KEYWORDS ป้องกัน false positive
- v0.4.16 — fix 5D: นำ 'ใช่' ออกจาก _SAVE_KEYWORDS + _SAVE_NEGATIVE_PREFIX ป้องกัน save false positive
- v0.4.17 — fix stale pending after save: receivedAgentEvent flag ป้องกัน save text ถูกตีความเป็น pending doc
- v0.4.18 — fix scroll lock: userScrolledUp flag หยุด auto-scroll เมื่อ user เลื่อนขึ้นอ่านระหว่าง streaming
- v0.4.19 — fix typing indicator ค้าง + discard notification ปนในเอกสาร: status type + always-hide on text
- v0.4.20 — feature pending doc modal: popup ถามก่อนยกเลิก บันทึกก่อน/ข้ามไป/ยกเลิก + auto-send queue
- v0.4.21 — WSL support: เพิ่ม start.sh/setup.sh, Flask host=0.0.0.0 สำหรับ access จาก Windows browser, แก้ Python 3.10 f-string fix
- v0.5.0 — Prototype phase: SQLite persistence (db.py), job history, session_id, /api/history routes, graceful DB degradation
- v0.5.1 — history.html: standalone history viewer page + Flask route /history
- v0.5.2 — setup.sh: auto-install WeasyPrint system libs + library verify step; requirements.txt เพิ่ม python-docx, openpyxl, weasyprint, markdown
- v0.6.0 — multi-format export: converter.py (.txt/.docx/.xlsx/.pdf) + format selector UI + pendingFormat state
- v0.6.1 — fix: suppress WeasyPrint verbose logs + _cleanup_old_temp ข้าม .gitkeep
- v0.6.2 — fix: format detection จาก message text override dropdown (ลบ pendingFormat lock)
- v0.7.0 — per-file format selector modal + cancel confirm modal สำหรับ PM multi-file saves
- v0.7.1 — fix: format popup แสดงสำหรับ single-agent doc ด้วย (HR/Accounting/Manager)
- v0.7.2 — fix: ลบ format dropdown ออกจาก input area (popup เป็นตัวเลือก format หลักแทน)
- v0.8.0 — feature: Workspace Picker Modal + ALLOWED_WORKSPACE_ROOTS env var + /api/workspaces + /api/workspace/new
- v0.8.1 — fix: test_cases.py เพิ่ม PM Agent tests + routing/keyword validation สำหรับทุก cases
- v0.8.2 — fix: Orchestrator + PM Agent retry up to 3 times on bad JSON format before raising error
- v0.8.3 — fix: sidebar file panel not refreshing after agent saves to a recreated workspace directory
- v0.8.4 — feat: HR/Accounting/Manager agents read workspace files before writing (READ_ONLY_TOOLS + tool allow-list enforcement)
- v0.8.5 — fix: agents read wrong workspace file as context + PM pending edit-intent now blocks instead of silently discarding
- v0.9.0 — feat: conversation memory — last 10 turns sent to Orchestrator + all agents for full context awareness
- v0.10.0 — feat: web search via DDGS — HR/Accounting/Manager agents ค้นหาข้อมูลอินเทอร์เน็ตได้
- v0.10.1 — fix: web_search infinite loop guard (MAX 3 calls) + fake tool call JSON detection
- v0.11.0 — feat: Chat Agent + friendly conversation mode — acknowledge style, soften tone

## Rules ที่ต้องทำตามเสมอ
- ภาษาไทยใน UI และ system prompts ทั้งหมด
- ทุก agent output ต้องมี disclaimer ว่าเป็น draft
- Error messages เป็นภาษาไทยที่ user เข้าใจ ไม่ใช่ technical
- ห้าม hardcode API key ใน code เด็ดขาด
- ก่อนเริ่มงานใหม่ทุกครั้ง อ่าน docs/poc-plan.md ก่อน
- **ทุกครั้งที่มีการเปลี่ยนแปลงโค้ดที่อาจส่งผลต่อเอกสาร ให้อัปเดตเอกสารที่เกี่ยวข้องทันที** ดูตารางด้านล่าง
- **ชื่อไฟล์ทุกไฟล์ที่สร้างต้องเป็นภาษาอังกฤษเท่านั้น** — สะท้อนเนื้อหาภายในไฟล์, ใช้ snake_case, ห้ามใช้ภาษาไทยหรือภาษาอื่น เช่น `employment_contract_somchai_2025.docx`, `invoice_project_alpha_001.xlsx`

### เอกสารที่ต้องอัปเดตเมื่อโค้ดเปลี่ยน

| เมื่อเปลี่ยน | อัปเดตเอกสารเหล่านี้ |
|---|---|
| version ใน index.html | CLAUDE.md (Version ปัจจุบัน + ประวัติ), CHANGELOG.md, PROJECT_SUMMARY.md (version + history table), docs/poc-plan.md (file tree), docs/project-plan.md (POC version), DEMO-READINESS-REPORT.md |
| UI feature ใหม่ (index.html) | PROJECT_SUMMARY.md (UI Architecture), DEMO-READINESS-REPORT.md (UI FEATURES), docs/poc-plan.md (progress list) |
| Agent ใหม่ หรือ agent logic เปลี่ยน (app.py) | PROJECT_SUMMARY.md (Agents table), docs/poc-plan.md (Agent table + progress), DEMO-READINESS-REPORT.md (Agent Routing Status) |
| โครงสร้างไฟล์เปลี่ยน | PROJECT_SUMMARY.md (โครงสร้างไฟล์), CLAUDE.md (โครงสร้างไฟล์), docs/poc-plan.md (file tree) |
| Demo use cases เปลี่ยน | PROJECT_SUMMARY.md (Demo Use Cases), docs/poc-plan.md (session log), DEMO-READINESS-REPORT.md (USE CASES STATUS), backup/demo-inputs.txt |

## Working Process Rules — Follow Every Task

กฎเหล่านี้ใช้กับทุกงาน ไม่ต้องรอให้บอก:

### 1. ทำความเข้าใจคำสั่งให้ชัดเจนก่อน
→ ก่อนวางแผนหรือลงมือทำ ต้องเข้าใจ scope, goal, และ constraint ให้ครบ
→ ถ้ามีส่วนไหนที่คลุมเครือ ให้ถามก่อน อย่าสมมติเอง

### 2. วางแผนละเอียดก่อนลงมือทำทุกครั้ง
→ ระบุไฟล์ที่จะแก้, สิ่งที่จะเปลี่ยน, และลำดับขั้นตอนให้ชัดเจน
→ แสดงแผนให้ user เห็นก่อนเริ่มลงมือ

### 3. คำนึงถึงไฟล์อื่นที่อาจได้รับผลกระทบเสมอ
→ ทุกครั้งที่แก้ไฟล์ใด ให้ตรวจสอบว่าไฟล์อื่นที่ import, reference, หรือ depend ได้รับผลกระทบหรือไม่
→ อย่าแก้แบบ isolated โดยไม่มองภาพรวม

### 4. หลังทำเสร็จ ให้ลิสต์ไฟล์ที่ได้รับผลกระทบทั้งหมดก่อน
→ ระบุชื่อไฟล์ + สิ่งที่เปลี่ยนไป + เหตุผลที่เปลี่ยน
→ ทำก่อนขั้นตอน update docs และ commit

### 5. อัปเดตไฟล์ที่ได้รับผลกระทบให้เป็นปัจจุบัน
→ ดูตาราง "เอกสารที่ต้องอัปเดตเมื่อโค้ดเปลี่ยน" ด้านบนเสมอ
→ อัปเดต inline ทันที อย่ารอไว้ทีหลัง

### 6. Commit ทุกครั้งที่มีการเปลี่ยนแปลงที่ส่งผลต่อการทำงานของโปรเจค
→ commit message ต้องระบุ version, ประเภท (fix/feature/docs), และสิ่งที่เปลี่ยน
→ bump version ใน index.html พร้อมกันทุกครั้ง

### 7. งานที่มีความเสี่ยงต่อโปรเจค ต้องถาม user ก่อนเสมอ
→ ตัวอย่างงานเสี่ยง: เปลี่ยน DB schema, refactor core routing, ลบไฟล์, แก้ auth flow
→ อธิบายความเสี่ยงให้ชัด + เสนอทางเลือก ก่อนขอ confirm

### 8. ดู subagents ที่มีก่อน และเลือกตัวที่ตรงกับงานมากที่สุด
→ อ่านรายชื่อจาก `.claude/agents/` ก่อนลงมือทุกครั้ง
→ ใช้ subagent ที่ความสามารถตรงกับงานที่สุด อย่าทำเองทั้งหมดถ้ามี subagent รองรับ

---

## Subagents Available — อ่านก่อนทุกงาน

ไฟล์อยู่ใน `.claude/agents/` — เลือกใช้ตาม trigger ด้านล่างเสมอ อย่าทำงานเองถ้ามี subagent รองรับ

| Subagent | Trigger — เรียกเมื่อ |
|---|---|
| `python-reviewer` | หลังแก้ .py ไฟล์ใดๆ (app.py, db.py, converter.py, mcp_server.py, test scripts) |
| `debug-assistant` | ทันทีที่มี error / traceback / unexpected output — รันก่อน fix เสมอ ห้าม fix เองโดยไม่ผ่าน agent นี้ |
| `security-checker` | ก่อน demo ทุกครั้ง, ก่อน git commit, เมื่อแก้ .env หรือ API key config |
| `thai-doc-checker` | หลัง agent สร้าง output ภาษาไทยทุกชิ้น (HR / Accounting / Manager / PM) |
| `ui-ux-reviewer` | หลังแก้ index.html หรือ history.html — ต้องผ่านก่อนถือว่า UI done |
| `frontend-developer` | ระหว่างพัฒนาหรือแก้ UI — ใช้คู่กับ ui-ux-reviewer |
| `db-checker` | หลังแก้ db.py หรือ converter.py, ก่อน demo เพื่อตรวจ DB health |
| `prompt-engineer` | เมื่อ agent output ผิด, routing ผิด agent, หรือเริ่มเขียน/แก้ system prompt |
| `demo-preparer` | เมื่อเตรียม demo, dry-run, หรือถามว่า "พร้อม demo ไหม" |
| `project-documenter` | ท้าย work session ทุกครั้ง |

---

## Agent Workflow Rules — Follow Automatically

These rules apply without needing to be asked. Non-negotiable.

### After writing or editing ANY .py file
→ ALWAYS run `python-reviewer` before considering done
→ Covers: app.py, db.py, converter.py, mcp_server.py, any test script

### After any error, exception, or unexpected output
→ ALWAYS run `debug-assistant` IMMEDIATELY — before attempting any fix
→ Do NOT try to fix the error yourself first

### After generating any Thai document output
→ ALWAYS run `thai-doc-checker`
→ Applies to all agents: HR, Accounting, Manager Advisor, PM Agent

### After writing or editing index.html or history.html
→ Run `frontend-developer` to verify SSE handling and UI states
→ Then run `ui-ux-reviewer` to validate from manager's perspective
→ Both must pass before UI work is considered done

### After editing db.py or converter.py
→ Run `db-checker` to verify integrity, graceful degradation, and export flow

### Before demo or dry-run — MANDATORY SEQUENCE
→ Step 1: Run `security-checker` first
→ Step 2: Run `db-checker` to verify DB health
→ Step 3: Run `demo-preparer` for full checklist
→ Do NOT skip any step even if "nothing changed"

### When agent output is wrong or routing misbehaves
→ Run `prompt-engineer` before manually editing any system prompt

### After any code change affecting documentation
→ Update related docs immediately — see table in "เอกสารที่ต้องอัปเดตเมื่อโค้ดเปลี่ยน"
→ Do NOT wait until end of session

### At end of each work session
→ Run `project-documenter` to update docs/poc-plan.md

### After finishing ALL tasks in a session — MANDATORY
→ Update ALL related documents listed in "เอกสารที่ต้องอัปเดตเมื่อโค้ดเปลี่ยน" before considering done
→ Verify: CLAUDE.md, CHANGELOG.md, PROJECT_SUMMARY.md, DEMO-READINESS-REPORT.md are in sync with current version
→ Do NOT mark work as complete if any doc still shows an older version number
→ **This is non-negotiable: no task is "done" until all related files are updated**

### After every version bump — MANDATORY git commit
→ Every time version is bumped in index.html, a git commit MUST be created immediately
→ Commit message format: `vX.X.X — [fix/feature/docs]: <brief description>`
→ Do NOT leave version bumps uncommitted
→ **Forgetting to commit after a version bump is an error, not a skip**