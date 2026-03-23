# Changelog — Internal AI Assistant POC

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
