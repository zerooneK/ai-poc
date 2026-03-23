# Changelog — Internal AI Assistant POC

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
