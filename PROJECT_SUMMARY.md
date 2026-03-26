# Project Summary — Internal AI Assistant POC
> ไฟล์นี้ใช้เพื่อให้ AI เข้าใจภาพรวมทั้งโปรเจกต์อย่างรวดเร็ว

---

## โปรเจกต์คืออะไร

**Internal AI Assistant Platform** — ระบบ AI สำหรับพนักงานภายในบริษัทไทย
พนักงานพิมพ์งานเป็นภาษาธรรมดา → Orchestrator เลือก Agent อัตโนมัติ → ได้เอกสารภาษาไทยพร้อมใช้

**เป้าหมายของ POC นี้:** Demo สดต่อหัวหน้าเพื่อขอ budget พัฒนาระบบ production จริง

**สถานะ:** Prototype phase · version **v0.10.1** · พร้อม demo

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + Flask + flask-cors |
| AI Provider | OpenRouter API (via OpenAI SDK) |
| Model | กำหนดผ่าน `OPENROUTER_MODEL` env var (default: `anthropic/claude-sonnet-4-5`) |
| Streaming | SSE (Server-Sent Events) via `client.chat.completions.create(stream=True)` |
| Frontend | index.html ไฟล์เดียว — dark mode default, ไม่มี framework |
| Markdown | marked.js (CDN) — render output เป็น HTML หลัง streaming เสร็จ |
| Icons | Material Symbols Outlined (Google Fonts) |
| Fonts | Inter + Sarabun (Google Fonts) |
| MCP Server | FastMCP (mcp_server.py) — 5 filesystem tools (Layer A/B) |
| File Watching | watchdog (Python) — real-time file panel updates |

---

## Architecture

```
User พิมพ์งาน (ภาษาไทย)
        ↓
[POST /api/chat] Flask backend
        ↓
Orchestrator (sync call, max_tokens=1024)
→ ตอบกลับ JSON: {"agent": "hr|accounting|manager|pm", "reason": "..."}
        ↓
Agent ที่เหมาะสม (streaming)
→ HR Agent        (max_tokens=7500)
→ Accounting Agent (max_tokens=6000)
→ Manager Advisor  (max_tokens=8000)
→ PM Agent         (max_tokens=8000, agentic loop with MCP tools)
        ↓
SSE stream → Frontend แสดงผล real-time
        ↓
[PM Agent only] Confirmation flow:
→ User types "บันทึก" → atomic move temp/ → workspace/
→ User types edit instruction → revise and re-stream
```

**SSE Event Types:** `status` → `agent` → `text` (streaming) → `done` | `error`

---

## Agents

| Agent | หน้าที่ | max_tokens | Tools |
|---|---|---|---|
| **Orchestrator** | วิเคราะห์งานและ route ไปหา agent ที่ถูกต้อง ตอบ JSON เท่านั้น | 1024 | — |
| **HR Agent** | สัญญาจ้าง, Job Description, นโยบาย, อีเมล HR | 7500 | list_files, read_file, web_search |
| **Accounting Agent** | Invoice (พร้อม VAT 7%), Expense Report (ไม่มี VAT), งบประมาณ | 6000 | list_files, read_file, web_search |
| **Manager Advisor** | Feedback พนักงาน (พร้อม script คำพูด), budget, ลำดับความสำคัญ, headcount | 8000 | list_files, read_file, web_search |
| **PM Agent** | งานที่ต้องการหลายแผนก → แยกเป็น subtasks → route ไป HR/Accounting/Manager → รวมผลและสร้างไฟล์ | 8000 | create_file, update_file, delete_file, list_files, read_file |

**กฎสำคัญของ Agents:**
- ทุก output ต้องมี disclaimer: `"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"`
- วันที่เป็น พ.ศ. เสมอ (ปัจจุบัน พ.ศ. 2569)
- VAT 7% เฉพาะ Invoice/ใบกำกับภาษี — ห้ามใช้กับ Expense Report
- Manager Advisor: ให้ script คำพูดจริง + แผนปฏิบัติได้ภายใน 48 ชั่วโมง

---

## โครงสร้างไฟล์

```
ai-poc/
├── app.py                   ← Flask backend + Orchestrator + Agents + PM Agent + Agentic loop + DB integration
├── db.py                    ← SQLite persistence layer (jobs, saved_files) — graceful degradation
├── converter.py             ← Multi-format export (.txt/.docx/.xlsx/.pdf) — deferred imports
├── mcp_server.py            ← MCP Filesystem Server (FastMCP) + 5 tools (Layer A/B)
├── index.html               ← Web UI ไฟล์เดียว (The Silent Concierge + chat bubbles + format popup)
├── history.html             ← Standalone job history viewer page (Flask route /history)
├── requirements.txt         ← flask, flask-cors, openai, python-dotenv, mcp, watchdog, python-docx, openpyxl, weasyprint, markdown
├── setup.sh                 ← auto-install: venv + pip + WeasyPrint system libs + Thai fonts + verify
├── start.sh                 ← run script: activate venv + flask run host=0.0.0.0 (WSL-compatible)
├── test_cases.py            ← Automated test (5 use cases) — PYTHONUTF8=1 python test_cases.py
├── quick-demo-check.py      ← Full validation script (7 checks รวม health)
├── smoke_test_phase0.py     ← Focused Phase 0 smoke test (5 checks, urllib-based, Thai-safe on Windows)
├── CHANGELOG.md             ← Version history
├── PROJECT_SUMMARY.md       ← ไฟล์นี้
├── CLAUDE.md                ← Rules สำหรับ Claude Code
├── PRE-DEMO-CHECKLIST.md    ← Checklist 30 นาทีก่อน demo
├── DEMO-READINESS-REPORT.md ← สรุปผลการตรวจสอบ demo readiness
├── .env                     ← OPENROUTER_API_KEY, OPENROUTER_MODEL, WORKSPACE_PATH (ห้าม commit)
├── .env.example             ← Template
├── .gitignore               ← exclude: .env, venv/, backup/screenshots/, workspace/*, temp/*, data/*
├── workspace/               ← workspace directory สำหรับ agent สร้างไฟล์ (gitignored ยกเว้น .gitkeep)
├── temp/                    ← staging area สำหรับไฟล์ที่รอ user confirm (gitignored ยกเว้น .gitkeep)
├── data/                    ← SQLite database directory — assistant.db สร้างอัตโนมัติ (gitignored)
├── backup/
│   ├── demo-inputs.txt      ← copy-paste inputs ทั้ง 6 cases พร้อมใช้
│   ├── demo-script.md       ← demo script พร้อม timing และ talking points
│   └── screenshots/         ← ภาพหน้าจอ backup (ไม่ commit)
└── docs/
    ├── poc-plan.md          ← แผน POC 2 คืน + session logs
    ├── project-plan.md      ← แผน production Phase 0-4 (8 สัปดาห์)
    └── phase-0-safe-execution-plan.md ← แผนการ execute Phase 0 อย่างปลอดภัย
```

---

## วิธีรันโปรเจกต์

```bash
# ติดตั้ง dependencies
pip install -r requirements.txt

# สร้าง .env จาก template
cp .env.example .env
# แล้วใส่ OPENROUTER_API_KEY จริง

# รัน server
python app.py
# เปิด http://localhost:5000

# รัน tests (Windows ต้องมี PYTHONUTF8=1)
set PYTHONUTF8=1 && .\venv\Scripts\python.exe test_cases.py
set PYTHONUTF8=1 && .\venv\Scripts\python.exe quick-demo-check.py
.\venv\Scripts\python.exe smoke_test_phase0.py
```

---

## Demo Use Cases (6 cases, ทดสอบแล้ว 6/6 PASS)

| # | Agent | Input |
|---|---|---|
| 1 | HR | ร่างสัญญาจ้างพนักงานชื่อ สมชาย ใจดี ตำแหน่ง นักบัญชี เงินเดือน 35,000 บาท เริ่มงาน 1 มกราคม 2568 |
| 2 | HR | สร้าง Job Description สำหรับตำแหน่ง HR Manager ในบริษัทขนาดกลาง |
| 3 | HR | ร่างอีเมลแจ้งพนักงานทุกคนเรื่องนโยบาย Work from Home ใหม่ สามารถทำงานจากบ้านได้สัปดาห์ละ 2 วัน |
| 4 | Accounting | สร้าง Invoice สำหรับ บริษัท ABC จำกัด สำหรับค่าบริการที่ปรึกษา เดือนธันวาคม 2567 จำนวน 50,000 บาท |
| 5 | Accounting | สรุปรายการค่าใช้จ่ายของแผนก Marketing เดือนนี้ แบ่งเป็น ค่าโฆษณา 30,000 ค่าจ้างฟรีแลนซ์ 15,000 ค่าเดินทาง 5,000 |
| 6 | Manager | ช่วยฉันวางแผนการพูดคุยกับพนักงานที่ส่งงานช้าและขาดงานบ่อย ฉันเป็น Team Lead และต้องการให้ Feedback อย่างสร้างสรรค์ |

---

## Version History

| Version | วันที่ | ประเภท | สิ่งที่เปลี่ยน |
|---|---|---|---|
| v0.1.0 | 23 มี.ค. 2569 | feat | initial POC — HR + Accounting + SSE streaming |
| v0.2.0 | 23 มี.ค. 2569 | feat | Manager Advisor agent + timer counter + copy button |
| v0.2.1 | 23 มี.ค. 2569 | fix | Manager badge แสดงผิด label/color |
| v0.2.2 | 23 มี.ค. 2569 | chore | Semantic versioning rule + CHANGELOG.md |
| v0.2.3 | 23 มี.ค. 2569 | docs | PROJECT_SUMMARY.md (ไฟล์นี้) |
| v0.3.0 | 23 มี.ค. 2569 | feat | UI redesign "The Silent Concierge" — Navbar + Sidebar + design tokens |
| v0.3.1 | 23 มี.ค. 2569 | feat | Markdown rendering (marked.js) + status-row solid background fix |
| v0.3.2 | 23 มี.ค. 2569 | feat | Auto-resize textarea (1 บรรทัด → max 5 บรรทัด) |
| v0.3.3 | 23 มี.ค. 2569 | feat | Input area redesign — button absolute inside container (ChatGPT style) |
| v0.3.4 | 23 มี.ค. 2569 | fix | Agent badge reserved space + idle state "รอคำสั่งงาน..." |
| v0.3.5 | 23 มี.ค. 2569 | feat | Nav-items → pill chips, dark mode สว่างขึ้น, secondary text สว่างขึ้น |
| v0.3.6 | 23 มี.ค. 2569 | feat | Typing indicator (3 bouncing dots) ก่อน streaming เริ่ม |
| v0.3.7 | 23 มี.ค. 2569 | fix | ai-accent-line สูงพอดี typing bubble ระหว่าง typing state |
| v0.3.8 | 23 มี.ค. 2569 | fix | "tokens"→"ตัวอักษร" + typing indicator ซ่อนเมื่อ error |
| v0.3.9 | 24 มี.ค. 2569 | feat | Chat bubble UI — user messages right, AI left, accumulated history |
| v0.4.0 | 24 มี.ค. 2569 | feat | PM Agent + MCP Filesystem (workspace selector, real-time file panel, agentic tool-calling loop) |
| v0.4.1 | 24 มี.ค. 2569 | feat | Confirmation flow frontend — pending state tracking, send pending_doc/pending_agent, input hint changes |
| v0.4.2 | 24 มี.ค. 2569 | fix | PM Agent JSON parse robustness (_extract_json helper) + sidebar badge overflow fix |
| v0.4.3 | 24 มี.ค. 2569 | feat | Temp staging flow — PM subtasks stream to temp/, confirm → atomic move to workspace; single-agent confirmation unchanged |
| v0.4.4 | 24 มี.ค. 2569 | fix | Pending doc discard bug — new requests treated as edit instead of new route; added `_DISCARD_KEYWORDS` detection in app.py |
| v0.4.5 | 24 มี.ค. 2569 | feat | Cancel pending button — "✕ ยกเลิก" button in UI below input when pending confirmation (client-side clear) |
| v0.4.8 | 24 มี.ค. 2569 | fix | Disable Flask debug mode by default; allow opt-in local debug via `FLASK_DEBUG=1` |
| v0.4.9 | 24 มี.ค. 2569 | fix | Restrict runtime workspace changes to directories under the project root |
| v0.4.10 | 24 มี.ค. 2569 | fix | Preserve pending confirmation state and avoid false save success when file creation fails |
| v0.4.11 | 24 มี.ค. 2569 | fix | Sanitize markdown output and replace risky frontend HTML injection with safer DOM rendering |
| v0.4.12 | 24 มี.ค. 2569 | fix | Add a focused Phase 0 smoke-test harness with Windows-safe Thai confirmation checks, retry, and timeout diagnostics |
| v0.4.13 | 24 มี.ค. 2569 | fix | เพิ่ม `done` event ใน outer except blocks ป้องกัน frontend ค้างเมื่อเกิด error |
| v0.4.14 | 24 มี.ค. 2569 | fix | PM subtask loop break เมื่อ subtask error ป้องกัน loop วิ่งต่อหลังพัง |
| v0.4.15 | 24 มี.ค. 2569 | fix | นำ 'งานใหม่'/'เริ่มใหม่' ออกจาก _DISCARD_KEYWORDS ป้องกัน false positive |
| v0.4.16 | 24 มี.ค. 2569 | fix | นำ 'ใช่' ออกจาก _SAVE_KEYWORDS + _SAVE_NEGATIVE_PREFIX ป้องกัน save false positive |
| v0.4.17 | 24 มี.ค. 2569 | fix | receivedAgentEvent flag ป้องกัน save text ถูกตีความเป็น pending doc หลัง save สำเร็จ |
| v0.4.18 | 24 มี.ค. 2569 | fix | userScrolledUp flag หยุด auto-scroll เมื่อ user เลื่อนขึ้นอ่านระหว่าง streaming |
| v0.4.19 | 24 มี.ค. 2569 | fix | typing indicator ค้าง + discard notification ปนในเอกสาร: เปลี่ยนเป็น status type + always-hide typing on text |
| v0.4.20 | 24 มี.ค. 2569 | feat | pending doc confirmation modal — popup ถามก่อนยกเลิก (บันทึกก่อน/ข้ามไป/ยกเลิก) + auto-send queue |
| v0.4.21 | 25 มี.ค. 2569 | feat | WSL support: start.sh/setup.sh, Flask host=0.0.0.0, Python 3.10 f-string fix |
| v0.5.0 | 25 มี.ค. 2569 | feat | Prototype phase: SQLite persistence (db.py), job history, session_id, /api/history routes, graceful DB degradation |
| v0.5.1 | 25 มี.ค. 2569 | feat | history.html: standalone history viewer page + Flask route /history |
| v0.5.2 | 25 มี.ค. 2569 | feat | setup.sh: auto-install WeasyPrint system libs + Thai fonts + verify step; requirements.txt เพิ่ม python-docx, openpyxl, weasyprint, markdown |
| v0.6.0 | 25 มี.ค. 2569 | feat | multi-format export: converter.py (.txt/.docx/.xlsx/.pdf) + format selector UI + pendingFormat state |
| v0.6.1 | 25 มี.ค. 2569 | fix | suppress WeasyPrint verbose logs + _cleanup_old_temp ข้าม .gitkeep |
| v0.6.2 | 25 มี.ค. 2569 | fix | format detection จาก message text override dropdown (ลบ pendingFormat lock) |
| v0.7.0 | 25 มี.ค. 2569 | feat | per-file format selector modal + cancel confirm modal สำหรับ PM multi-file saves |
| v0.7.1 | 25 มี.ค. 2569 | fix | format popup แสดงสำหรับ single-agent doc ด้วย (HR/Accounting/Manager) |
| v0.7.2 | 25 มี.ค. 2569 | fix | ลบ format dropdown ออกจาก input area (popup เป็นตัวเลือก format หลักแทน) |
| v0.8.0 | 25 มี.ค. 2569 | feat | Workspace Picker Modal — คลิกเลือก workspace + ALLOWED_WORKSPACE_ROOTS + /api/workspaces + /api/workspace/new |
| v0.8.1 | 25 มี.ค. 2569 | fix | test_cases.py เพิ่ม PM Agent tests + routing/keyword validation สำหรับทุก cases |
| v0.8.2 | 25 มี.ค. 2569 | fix | Orchestrator + PM Agent retry up to 3 times on bad JSON format before raising error |
| v0.8.3 | 25 มี.ค. 2569 | fix | sidebar file panel not refreshing after agent saves to a recreated workspace directory |
| v0.8.4 | 25 มี.ค. 2569 | feat | HR/Accounting/Manager agents อ่านไฟล์ใน workspace ก่อนสร้างเอกสาร (READ_ONLY_TOOLS + allow-list enforcement) |
| v0.8.5 | 25 มี.ค. 2569 | fix | agents อ่านไฟล์ workspace ผิดบริบท + PM pending edit-intent แจ้งเตือนแทนลบไฟล์ silent |
| v0.9.0 | 25 มี.ค. 2569 | feat | conversation memory — last 10 turns ส่งไปยัง Orchestrator + agents ทุก request |
| v0.10.0 | 26 มี.ค. 2569 | feat | web search via DDGS — HR/Accounting/Manager agents ค้นหาข้อมูลอินเทอร์เน็ตได้ |
| v0.10.1 | 26 มี.ค. 2569 | fix | web_search infinite loop guard + fake tool call JSON detection |

**กฎ versioning:** Minor bump (0.X.0) = agent/feature ใหม่ · Patch bump (0.0.X) = fix/tweak
**ทุก commit ต้อง bump version ใน `index.html` และเพิ่ม entry ใน `CHANGELOG.md`**

---

## UI Architecture (v0.8.x)

index.html ใช้ design system "The Silent Concierge":

```
Fixed Sidebar (256px)
  ├── Brand icon + "AI Assistant" + "INTERNAL POC"
  ├── Workspace Selector (dropdown + เลือก folder)
  ├── Agent badge (reserved space เสมอ — idle state "รอคำสั่งงาน..." พร้อม dashed border)
  ├── Nav chips × 6 (flex-wrap pill chips, border-radius: 99px, hover: primary border)
  ├── File Panel (real-time list จาก workspace via SSE /api/workspace/files/stream)
  └── Footer: theme toggle + model pill + POC warning

Fixed Navbar (left: 256px, frosted glass)
  ├── App title + subtitle (agents list)
  └── Version tag (right)

Main area (margin-left: 256px)
  ├── chat-container (scrollable, chat history bubbles)
  │   ├── User message bubbles (right side, primary background)
  │   ├── AI message bubbles (left side, secondary background)
  │   │   ├── ai-accent-line (opacity 0→1 ระหว่าง streaming)
  │   │   ├── typing-indicator (3 bouncing dots — แสดงระหว่าง agent event ถึง text chunk แรก)
  │   │   └── message-content (plain text ระหว่าง stream → HTML หลัง done, marked.js)
  │   └── Confirmation state (PM Agent only):
  │       - แสดง "พิมพ์ 'บันทึก' เพื่อยืนยัน หรือบอกให้แก้ไข"
  │       - Input hint เปลี่ยน placeholder: "💬 พิมพ์ บันทึก หรือ ✏️ ระบุสิ่งที่แก้ไข"
  │       - "✕ ยกเลิก" button ปรากฏเมื่อ pending confirmation
  │       - Confirmation modal: popup ถามก่อนยกเลิก (บันทึกก่อน/ข้ามไป/ยกเลิก) + auto-send queue
  └── Fixed input-footer
      ├── input-wrapper (backdrop-filter blur)
      └── input-container (position: relative, border-radius: 20px)
          ├── textarea (auto-resize 1-5 บรรทัด, padding-right: 52px)
          └── send-btn (absolute bottom-right, gradient background)
```

**Markdown Rendering Flow:**
- ระหว่าง streaming: `output.textContent = outputText` (plain text)
- เมื่อ `done` event: `output.innerHTML = marked.parse(outputText)` → switch เป็น HTML

**Scroll Behavior:**
- Auto-scroll ระหว่าง streaming เมื่อ user ไม่ได้เลื่อนขึ้น
- `userScrolledUp` flag หยุด auto-scroll เมื่อ user เลื่อนขึ้นอ่าน (v0.4.18)

---

## Known Issues & Quirks

| ปัญหา | วิธีแก้ |
|---|---|
| Reasoning models (minimax, deepseek-r1) return `content=None` | Orchestrator ต้องใช้ `max_tokens ≥ 1024` |
| Windows terminal แสดงภาษาไทยแตก | prefix ด้วย `PYTHONUTF8=1` ทุกครั้ง |
| Windows shell smoke test ส่ง `บันทึก` / `ยกเลิก` แล้วกลายเป็น `??????` | ใช้ `.\\venv\\Scripts\\python.exe`, ส่ง JSON เป็น UTF-8, และถ้าเขียน inline script บน Windows ให้ใช้ Unicode escape สำหรับคำภาษาไทย |
| Model name ใน sidebar ไม่ตรง | ดึงจาก `/api/health` อัตโนมัติตอนโหลดหน้า |
| marked.js ต้องการ internet | โหลดจาก CDN — ถ้า offline จะ fallback เป็น plain text |
| Pending doc + new request → treated as edit (v0.4.4 fix) | เพิ่ม `_DISCARD_KEYWORDS` detection ใน app.py |

---

## สิ่งที่ Prototype นี้ไม่มี (ต้องบอกหัวหน้าตรงๆ)

- ❌ Login / Authentication
- ❌ LangGraph (ใช้ direct API call + agentic loop แทน)
- ✅ บันทึกประวัติการใช้งาน — SQLite + /history page (เพิ่มแล้ว v0.5.0)
- ✅ Database — SQLite graceful degradation (เพิ่มแล้ว v0.5.0)
- ✅ Multi-format export — .md/.txt/.docx/.xlsx/.pdf (เพิ่มแล้ว v0.6.0)

---

## Production Roadmap (ถ้าได้ budget)

| Phase | สิ่งที่เพิ่ม | เวลา |
|---|---|---|
| 1 | Flask + LangGraph + MCP + SSE จริง | 2-3 สัปดาห์ |
| 2 | React UI + file upload + history | 2 สัปดาห์ |
| 3 | Auth + Security + Deploy on company server | 2 สัปดาห์ |
| 4 | Agent เพิ่ม (Legal, IT, Marketing) + feedback loop | ต่อเนื่อง |

**รวม Time to MVP: ~7-8 สัปดาห์**
**ค่าใช้จ่าย:** ~$416-624/เดือน สำหรับ 30 คน (Claude Sonnet via OpenRouter)

---

## Rules สำคัญสำหรับ AI ที่ทำงานในโปรเจกต์นี้

1. ทุกครั้งที่แก้ `.py` → รัน `python-reviewer` ก่อน done
2. ทุกครั้งที่มี error → รัน `debug-assistant` ทันที
3. ทุกครั้งที่สร้าง Thai document output → รัน `thai-doc-checker`
4. ทุกครั้งที่แก้ `index.html` → รัน `frontend-developer` แล้วตามด้วย `ui-ux-reviewer`
5. ก่อน demo → รัน `security-checker` แล้วตามด้วย `demo-preparer`
6. ท้ายทุก session → รัน `project-documenter` อัปเดต `docs/poc-plan.md`
7. **ทุก commit** → bump version ใน `index.html` + เพิ่ม entry ใน `CHANGELOG.md`
8. **หลังทำงานทุกครั้ง** → อัปเดต CLAUDE.md, CHANGELOG.md, PROJECT_SUMMARY.md, DEMO-READINESS-REPORT.md ให้ sync กับ version ปัจจุบันก่อนถือว่าเสร็จ
