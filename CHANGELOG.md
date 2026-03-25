# Changelog — Internal AI Assistant POC

## [v0.7.0] — 25 มีนาคม 2569 · feature
- เพิ่ม file format selector modal: popup แสดง per-file format dropdown ก่อนบันทึก PM files
- เพิ่ม cancel confirm modal: ยืนยันก่อนยกเลิก PM files พร้อมแสดงจำนวนไฟล์
- intercept save/cancel intent ฝั่ง frontend ก่อน submit (ไม่ผ่าน server)
- app.py: handle_pm_save รับ output_formats list (per-file), fallback ไป output_format ถ้าไม่มี
- เพิ่ม _isSaveIntentJS / _isCancelIntentJS สำหรับ PM modal intercept

---

## [v0.6.2] — 25 มีนาคม 2569 · fix
- fix: format detection จาก message text — "save as pdf", "บันทึกเป็น excel" override dropdown
- priority: message keyword → dropdown value (pendingFormat lock ถูกเอาออก)
- dropdown อัปเดตอัตโนมัติเมื่อ detect format จาก message

---

## [v0.6.1] — 25 มีนาคม 2569 · fix
- fix: suppress WeasyPrint/fontTools verbose font subsetting logs (ตั้ง log level ERROR/WARNING)
- fix: _cleanup_old_temp() ข้าม .gitkeep ป้องกันถูกลบทุกครั้งที่ส่ง request

---

## [v0.6.0] — 25 มีนาคม 2569 · feature
- เพิ่ม `converter.py`: แปลง markdown → .txt / .docx / .xlsx / .pdf ที่ save time
- .docx: parse headings, lists, tables, bold ผ่าน python-docx
- .xlsx: ดึง markdown table → openpyxl rows; fallback เนื้อหาทั้งหมดใน A1
- .pdf: markdown → HTML → WeasyPrint พร้อม Thai font (Norasi/Garuda)
- อัปเดต `app.py`: `_suggest_filename` รองรับ extension, `handle_save` และ `handle_pm_save` รับ `output_format`
- อัปเดต `index.html`: format selector dropdown (.md/.txt/.docx/.xlsx/.pdf) ใน input area
- `pendingFormat` lock format ตอน doc pending, restore ผ่าน previousPendingState

---

## [v0.5.2] — 25 มีนาคม 2569 · feature
- อัปเดต `setup.sh`: ติดตั้ง WeasyPrint system libs อัตโนมัติ (libpango, libharfbuzz, libffi, libjpeg, libopenjp2, fonts-thai-tlwg)
- เพิ่ม library verify step ใน setup.sh (ตรวจสอบ flask, openai, docx, openpyxl, weasyprint, markdown)
- อัปเดต `requirements.txt`: เพิ่ม python-docx, openpyxl, weasyprint, markdown

---

## [v0.5.1] — 25 มีนาคม 2569 · feature
- เพิ่ม `history.html` — หน้าดูประวัติ job แบบ standalone (dark theme เดียวกับ main UI)
- Stats bar: job ทั้งหมด, สำเร็จ, ไฟล์บันทึก, error
- Job card: agent badge, status dot, truncated input, วันที่
- คลิก card เพื่อ expand: แสดง output text (markdown rendered) + file chips
- เพิ่ม Flask route `/history` เสิร์ฟ `history.html`
- Back button กลับหน้าหลัก

---

## [v0.5.0] — 25 มีนาคม 2569 · feature
- เพิ่ม SQLite persistence layer (`db.py`) — บันทึกทุก job, agent routing, output text, และไฟล์ที่ save
- DB schema: 2 ตาราง (`jobs`, `saved_files`) พร้อม WAL mode + foreign keys + index
- Graceful degradation: DB error ไม่กระทบ chat flow — ถ้า DB ใช้ไม่ได้ระบบยังทำงานปกติ
- Zombie job cleanup: job ที่ค้าง `pending` เกิน 1 ชั่วโมงถูก mark เป็น `error` อัตโนมัติทุก startup
- เพิ่ม `session_id` (localStorage UUID) ส่งมากับทุก request เพื่อเตรียมรองรับ auth
- เพิ่ม `/api/history` และ `/api/history/<job_id>` routes
- อัปเดต `/api/health` ให้รายงานสถานะ DB
- เพิ่ม `data/` directory (gitignored) สำหรับเก็บ `assistant.db`
- Prototype phase เริ่มต้น: v0.5.x

---

## [v0.4.21] — 24 มีนาคม 2569 · fix
- เพิ่ม `start.sh` และ `setup.sh` สำหรับรัน app บน WSL โดยตรง
- เปลี่ยน Flask host เป็น `0.0.0.0` (configurable ด้วย `FLASK_HOST`) เพื่อให้เข้าถึงได้จาก Windows browser ผ่าน WSL
- อัปเดต CORS origins รองรับการเข้าถึงผ่าน WSL network
- แก้ Python 3.10 SyntaxError: backslash ใน nested f-string expression

---

## [v0.4.20]
---

## [v0.4.12] — 24 มีนาคม 2569 · fix
- เพิ่ม `smoke_test_phase0.py` เพื่อตรวจ Phase 0 hardening ด้วย Python stdlib (`urllib`) โดยไม่พึ่ง `requests`
- ทำให้ smoke test คำยืนยันภาษาไทย (`บันทึก` / `ยกเลิก`) ไม่ให้ได้ false negative จาก Windows shell encoding โดยใช้ UTF-8 JSON และ Unicode escape
- เพิ่ม retry แบบแคบๆ สำหรับ `basic chat` และจับ transport timeout/error ให้สคริปต์รายงาน FAIL พร้อมสาเหตุแทนการ crash
- อัปเดตเอกสารที่เกี่ยวข้องให้สะท้อน root cause ของ false alarm และวิธีรัน smoke test ที่ถูกต้องบน Windows

---

## [v0.4.11] — 24 มีนาคม 2569 · fix
- ลด XSS risk ฝั่ง frontend โดยเปลี่ยนการ render ข้อมูลจาก server/LLM หลายจุดไปใช้ DOM API แทน `innerHTML`
- sanitize markdown output ก่อนแทรกกลับเข้า DOM
- harden file list, agent badge, PM plan, tool result, และ error rendering ให้ปลอดภัยขึ้น

---

## [v0.4.10] — 24 มีนาคม 2569 · fix
- แยกกรณี `save_failed` ออกจาก success path ของการบันทึกไฟล์ฝั่ง single-agent
- ป้องกันการแสดงข้อความสำเร็จปลอมเมื่อ `create_file` ล้มเหลว
- คง pending confirmation state เดิมใน frontend เมื่อการบันทึกล้มเหลวหรือ request ยืนยันสะดุด

---

## [v0.4.9] — 24 มีนาคม 2569 · fix
- จำกัดการเปลี่ยน workspace ผ่าน `POST /api/workspace` ให้อยู่ภายใต้ root ของโปรเจกต์เท่านั้น
- คงรูปแบบ API เดิมไว้เพื่อลดผลกระทบกับ frontend ที่มีอยู่
- อัปเดตเอกสารให้สะท้อนข้อจำกัดใหม่ของ workspace selector/runtime

---

## [v0.4.8] — 24 มีนาคม 2569 · fix
- ปิด Flask debug mode เป็นค่าเริ่มต้นสำหรับการรันปกติ
- เพิ่มการเปิด debug ผ่าน environment variable `FLASK_DEBUG=1` แทนการ hardcode ใน `app.py`
- อัปเดตเอกสาร setup/runtime ให้ตรงกับพฤติกรรมใหม่ของ backend

---

## [v0.4.7] — 24 มีนาคม 2569 · fix
- **`_is_edit_intent()`**: เพิ่ม keyword set สำหรับคำสั่งแก้ไข (แก้ไข, ปรับ, เพิ่ม, ลบ, เปลี่ยน, edit, modify ฯลฯ)
- Single-agent pending block ตรวจสอบ 4 cases ชัดเจน: save → บันทึก / discard → ยกเลิก / edit intent → revise / **อื่นๆ = งานใหม่ → fall through Orchestrator**
- แก้ปัญหา: ส่งงานใหม่ขณะ pending → agent เดิมถูกเรียกแทน Orchestrator เลือกใหม่

---

## [v0.4.6] — 24 มีนาคม 2569 · fix
- **Fall-through routing**: เมื่อ user ส่งงานใหม่ขณะมี pending state → ยกเลิกไฟล์เดิมแล้ว **ส่งงานใหม่ไปยัง Orchestrator ต่อ** (ไม่ตัดจบอีกต่อไป)
- เพิ่ม `_is_pure_discard()` helper — ตรวจสอบว่า message เป็นแค่ keyword ยกเลิกล้วนๆ (exact match) ไม่ใช่ substring
- PM pending block: save → done+return / pure discard → confirm+done+return / งานใหม่ → แจ้ง "ยกเลิกแล้ว" แล้ว **fall through ไปยัง Orchestrator**
- Single-agent pending block: เพิ่ม branch เดียวกัน — pure discard → stop, discard+งานใหม่ → fall through

---

## [v0.4.5] — 24 มีนาคม 2569 · fix
- **✕ ยกเลิก button**: ปรากฏใต้ input เฉพาะเมื่ออยู่ใน confirmation state — คลิกเพื่อ clear pending state ทันที (client-side, ไม่ต้องส่ง request)
- **Discard keywords backend**: เพิ่ม `_is_discard_intent()` — ตรวจจับ "ยกเลิก", "cancel", "งานใหม่" ฯลฯ ใน single-agent pending flow
- แก้ bug: ส่งงานใหม่ขณะมี pending doc → ถูกตีความเป็น edit แทน → ตอนนี้กด ✕ หรือพิมพ์ "ยกเลิก" เพื่อ clear แล้วส่งงานใหม่ผ่าน Orchestrator ได้
- Hint text ปรับเป็น "💬 พิมพ์ บันทึก หรือ ✏️ ระบุสิ่งที่แก้ไข" ชัดเจนขึ้น

---

## [v0.4.4] — 24 มีนาคม 2569 · fix
- **PM Agent max_tokens**: เพิ่มจาก 1024 → 6000 — แก้ปัญหา subtask JSON ถูกตัดกลางคัน
  (1024 ไม่เพียงพอเมื่อ task descriptions ยาวแบบ self-contained)
- เพิ่ม `finish_reason` logging สำหรับ Orchestrator และ PM Agent
  เพื่อตรวจจับการ truncation ในอนาคต (warning เมื่อ finish_reason == 'length')

---

## [v0.4.3] — 24 มีนาคม 2569 · feat
- **Temp staging flow**: PM subtasks ใช้ `stream_agent()` แทน `run_agent_with_tools()` — stream เนื้อหาเต็มให้ user เห็น real-time
- **Temp directory**: `temp/` staging area — ไฟล์รอ confirm ที่นี่ ไม่ปรากฏใน workspace/file panel
- `_write_temp()` + `_move_to_workspace()` helpers — `os.replace()` atomic move
- `_cleanup_old_temp()` — ลบ temp files เก่ากว่า 1 ชั่วโมงอัตโนมัติ
- `handle_pm_save()` — รับ `pending_temp_paths[]` → move ทุกไฟล์ไปยัง workspace
- **PM confirmation flow**: หลัง PM tasks เสร็จ → hint "💾 พิมพ์ บันทึก เพื่อบันทึก N ไฟล์"
- Frontend: `pendingTempPaths[]` + `pending_file` SSE event + `_updateInputHint(isPending, fileCount)`

---

## [v0.4.2] — 23 มีนาคม 2569 · fix
- **PM Agent JSON parse**: เพิ่ม `_extract_json()` helper — strip code fences (ทุก variant), slice `{...}` จาก LLM output ก่อน parse
- **PM_PROMPT hardened**: เปิด prompt ด้วย OUTPUT FORMAT — CRITICAL, ห้าม code fences ซ้ำท้าย prompt
- **Orchestrator JSON parse**: ใช้ `_extract_json()` แทน inline replace chain
- **Subtask validation**: filter subtasks ที่ `agent` ไม่ใช่ hr/accounting/manager ออกก่อน execute
- **Sidebar badge overflow**: เพิ่ม `max-height: 96px`, `overflow: hidden`, `word-break: break-word` ใน `.agent-badge`
- **Badge reason clamp**: เพิ่ม `.agent-badge-reason` class (2-line clamp) แทน inline style

---

## [v0.4.1] — 23 มีนาคม 2569 · feat
- Confirmation flow (frontend): AI generates document → asks for edit or save → user types "บันทึก" or edit instruction
- State tracking: `pendingDoc`, `pendingAgent`, `isPendingConfirmation`, `wasPMTask`, `lastAgent`
- Input hint ไฮไลท์เป็นสีหลักเมื่ออยู่ใน confirmation state: "💬 พิมพ์ บันทึก เพื่อบันทึกไฟล์ หรือระบุสิ่งที่ต้องการแก้ไข"
- ส่ง `pending_doc` + `pending_agent` ไปกับ request ถัดไปเมื่ออยู่ใน pending state
- PM task ไม่เข้า pending flow (auto-save คงเดิม)

---

## [v0.4.0] — 23 มีนาคม 2569 · feat (Minor)
- **PM Agent**: แตก task ที่ครอบคลุมหลาย domain ออกเป็น subtasks พร้อมกำหนด Agent ที่เหมาะสม
- **MCP Filesystem**: Python FastMCP server + 5 tools (create/read/update/delete/list files)
- **Agentic Loop**: LLM → tool_calls → execute → feed back → repeat (max 5 รอบ) สำหรับทุก agent
- **Workspace Selector**: เลือก directory ได้ใน navbar, กำหนดขอบเขตการทำงานของ agent
- **Real-time File Panel**: sidebar แสดงไฟล์ใน workspace แบบ live (SSE + watchdog)
- **New endpoints**: GET/POST /api/workspace, GET /api/files, GET /api/files/stream
- Path traversal prevention: agent ออกนอก workspace ไม่ได้

---

## [v0.3.9] — 23 มีนาคม 2569 · feat
- Chat bubble UI: user message แสดงเป็น bubble ขวา, AI response แสดงซ้าย
- ประวัติสนทนาสะสมใน chat log (ไม่ clear ทุก send)
- สร้าง DOM elements ใหม่ต่อทุก message (`.msg-user`, `.msg-ai-container`, `.msg-ai-body`)
- `copyOutput()` copy จาก AI bubble ล่าสุด (`.output-area` สุดท้าย)
- แทน static `#outputContainer` ด้วย dynamic `.chat-log#chatLog`

---

## [v0.3.8] — 23 มีนาคม 2569 · fix
- แก้ status bar: "tokens" → "ตัวอักษร" (ตัวเลขที่แสดงคือจำนวนตัวอักษร ไม่ใช่ API tokens)
- แก้ typing indicator ค้างเมื่อเกิด error: ซ่อน typing dots และลบ class `.typing` ทั้งใน SSE error event และ catch block

---

## [v0.3.7] — 23 มีนาคม 2569 · fix
- ai-accent-line สูงพอดีกับ typing bubble ระหว่าง typing state (`.output-container.typing` class)
- เส้นยังยืดตาม text เหมือนเดิมเมื่อ streaming เริ่ม

---

## [v0.3.6] — 23 มีนาคม 2569 · feat
- Typing indicator: 3 จุดเด้งใน output area ระหว่างรอ agent ตอบกลับ (เหมือน chat bubble)
- แสดงเมื่อ `agent` event มาถึง → ซ่อนเมื่อข้อความแรกเริ่ม stream
- CSS `@keyframes typing-bounce` + `.typing-indicator` พร้อม stagger delay

---

## [v0.3.5] — 23 มีนาคม 2569 · feat
- Nav-items เปลี่ยนเป็น pill chips (flex-wrap, border-radius: 99px, border)
- Hover: background + primary border แทน slide animation
- Dark mode สว่างขึ้น: bg #0B0E14→#13171f, surface #151921→#1b2130
- Secondary text สว่างขึ้น: --on-surface-2 #abb3b7→#c8d2d8

---

## [v0.3.4] — 23 มีนาคม 2569 · fix
- Sidebar Agent badge: reserved space ตลอดเวลา (ไม่ใช้ display:none อีกต่อไป)
- Idle state แสดง "รอคำสั่งงาน..." พร้อม dashed border จาง
- ตัวอย่างงานไม่ขยับขึ้นลงอีกไม่ว่า agent จะ active หรือไม่

---

## [v0.3.3] — 23 มีนาคม 2569 · feat
- Input area redesign: button ย้ายเข้าไปอยู่ใน container (absolute bottom-right) สไตล์ ChatGPT/Claude
- เพิ่ม `.input-wrapper` (backdrop-filter blur) + `.input-container` (position: relative, border-radius: 20px)
- textarea: padding-right: 52px ป้องกันข้อความทับปุ่ม, max-height 200px
- send button: gradient background, opacity transition
- เพิ่ม input-hint "INTERNAL POC · DRAFT OUTPUT ONLY" ด้านล่าง input box

---

## [v0.3.2] — 23 มีนาคม 2569 · feat
- Auto-resize textarea: เริ่มต้น 1 บรรทัด → ขยายตาม content (max 5 บรรทัด / 140px)
- Reset กลับ 1 บรรทัดอัตโนมัติหลัง send
- fillInput() (nav-item click) trigger resize ด้วย

---

## [v0.3.1] — 23 มีนาคม 2569 · feat
- เพิ่ม Markdown rendering ด้วย marked.js (CDN)
- ระหว่าง streaming แสดงเป็น plain text — switch เป็น rendered HTML ตอน done
- เพิ่ม CSS สำหรับ markdown elements: h1-h3, table, code, blockquote, ul/ol, hr
- แก้ status-row พื้นหลังทึบ (`background: var(--bg)`) ป้องกัน text ทับกันเมื่อ scroll

---

## [v0.3.0] — 23 มีนาคม 2569 · feat
**UI Redesign — "The Silent Concierge"**
- ออกแบบ UI ใหม่ทั้งหมดตาม design system "High-End Editorial"
- เพิ่ม fixed Navbar (frosted glass, app title, version tag)
- ออกแบบ Sidebar ใหม่: Material Symbols icons, slide hover effect, model pill ใน footer
- Floating input-footer พร้อม gradient fade และ rounded input-box
- AI accent line (primary color) ปรากฏระหว่าง streaming ด้วย `.streaming` CSS class
- CSS Custom Properties สำหรับ dark/light mode (dark default) ผ่าน `body.light-mode`
- ฟอนต์: Inter + Sarabun + Material Symbols Outlined
- ทุก JS logic เดิมยังคงสมบูรณ์ (SSE, copy, timer, modelName, theme toggle)

---

## [v0.2.3] — 23 มีนาคม 2569 · docs
- เพิ่ม PROJECT_SUMMARY.md — ภาพรวมทั้งโปรเจกต์สำหรับ onboard AI ในการสนทนาใหม่
- ครอบคลุม: architecture, agents, file structure, run commands, version history, rules

รูปแบบ: [v0.MINOR.PATCH] — วันที่ · ประเภท · รายละเอียด

---

## [v0.2.2] — 23 มีนาคม 2569 · chore
- เปลี่ยนรูปแบบ version เป็น semantic versioning (v0.MINOR.PATCH)
- เพิ่มกฎ versioning ใน CLAUDE.md พร้อม version history

## [v0.2.1] — 23 มีนาคม 2569 · fix
- แก้ bug: Agent badge แสดง "Accounting Agent" แทน "Manager Advisor"
- เพิ่ม CSS class `agent-manager` สีม่วง (dark + light mode)
- แก้ sidebar footer: เพิ่ม Manager ในรายการ agents

## [v0.2.0] — 23 มีนาคม 2569 · feat
**Manager Advisor Agent (ใหม่)**
- เพิ่ม `MANAGER_PROMPT`: เชี่ยวชาญการบริหารทีมสำหรับ Team Lead
  - ครอบคลุม: Feedback, budget, ลำดับความสำคัญ, ความขัดแย้งในทีม, headcount
  - ให้ Script คำพูดจริงสำหรับการ feedback พนักงาน
  - ผลลัพธ์ทำได้ภายใน 48 ชั่วโมง
- อัปเดต Orchestrator: รองรับ routing 3 agents (hr / accounting / manager)
- อัปเดต generate(): system_prompt, agent_label, agent_max_tokens สำหรับ manager

**UI Improvements**
- เพิ่ม Processing time counter: "✅ เสร็จสิ้น · X.X วินาที · X,XXX tokens"
- เพิ่มปุ่ม Copy to clipboard (แสดงหลัง done event)

## [v0.1.0] — 23 มีนาคม 2569 · feat (initial)
**Core System**
- Flask backend + SSE streaming (Server-Sent Events)
- Multi-agent routing: Orchestrator → HR Agent / Accounting Agent
- OpenAI SDK เชื่อมต่อ OpenRouter API
- Model กำหนดผ่าน `OPENROUTER_MODEL` env var (ไม่ต้องแก้ code)

**HR Agent**
- สัญญาจ้างพนักงาน (ตามกฎหมายแรงงานไทย)
- Job Description
- อีเมลแจ้งนโยบายพนักงาน

**Accounting Agent**
- Invoice / ใบกำกับภาษี (พร้อม VAT 7%, เลขผู้เสียภาษี)
- สรุปค่าใช้จ่าย (ไม่มี VAT)
- ใช้วันที่ พ.ศ. 2569

**Frontend**
- Dark mode default, toggle light/dark พร้อม localStorage
- Enter ส่ง, Shift+Enter ขึ้นบรรทัดใหม่
- Agent badge แสดงสีตาม agent (green=HR, purple=Accounting)
- Model name ดึงจาก `/api/health` อัตโนมัติ

**Error Handling**
- Input validation (max 5,000 ตัวอักษร)
- API errors: RateLimitError, APITimeoutError, APIError
- Generic error message ภาษาไทย (ไม่ leak technical details)

---

_ทุก version มี AI disclaimer ท้ายเอกสาร: "⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"_
