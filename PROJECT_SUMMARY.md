# Project Summary — Internal AI Assistant POC
> ไฟล์นี้ใช้เพื่อให้ AI เข้าใจภาพรวมทั้งโปรเจกต์อย่างรวดเร็ว

---

## โปรเจกต์คืออะไร

**Internal AI Assistant Platform** — ระบบ AI สำหรับพนักงานภายในบริษัทไทย
พนักงานพิมพ์งานเป็นภาษาธรรมดา → Orchestrator เลือก Agent อัตโนมัติ → ได้เอกสารภาษาไทยพร้อมใช้

**เป้าหมายของ POC นี้:** Demo สดต่อหัวหน้าเพื่อขอ budget พัฒนาระบบ production จริง

**สถานะ:** POC เสร็จสมบูรณ์ 100% · version **v0.3.1** · พร้อม demo

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

---

## Architecture

```
User พิมพ์งาน (ภาษาไทย)
        ↓
[POST /api/chat] Flask backend
        ↓
Orchestrator (sync call, max_tokens=1024)
→ ตอบกลับ JSON: {"agent": "hr|accounting|manager", "reason": "..."}
        ↓
Agent ที่เหมาะสม (streaming)
→ HR Agent        (max_tokens=7500)
→ Accounting Agent (max_tokens=6000)
→ Manager Advisor  (max_tokens=8000)
        ↓
SSE stream → Frontend แสดงผล real-time
```

**SSE Event Types:** `status` → `agent` → `text` (streaming) → `done` | `error`

---

## Agents

| Agent | หน้าที่ | max_tokens |
|---|---|---|
| **Orchestrator** | วิเคราะห์งานและ route ไปหา agent ที่ถูกต้อง ตอบ JSON เท่านั้น | 1024 |
| **HR Agent** | สัญญาจ้าง, Job Description, นโยบาย, อีเมล HR | 7500 |
| **Accounting Agent** | Invoice (พร้อม VAT 7%), Expense Report (ไม่มี VAT), งบประมาณ | 6000 |
| **Manager Advisor** | Feedback พนักงาน (พร้อม script คำพูด), budget, ลำดับความสำคัญ, headcount | 8000 |

**กฎสำคัญของ Agents:**
- ทุก output ต้องมี disclaimer: `"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"`
- วันที่เป็น พ.ศ. เสมอ (ปัจจุบัน พ.ศ. 2569)
- VAT 7% เฉพาะ Invoice/ใบกำกับภาษี — ห้ามใช้กับ Expense Report
- Manager Advisor: ให้ script คำพูดจริง + แผนปฏิบัติได้ภายใน 48 ชั่วโมง

---

## โครงสร้างไฟล์

```
ai-poc/
├── app.py                   ← Flask backend + Orchestrator + Agents (MAIN FILE)
├── index.html               ← Web UI ไฟล์เดียว (The Silent Concierge design)
├── requirements.txt         ← flask, flask-cors, openai, python-dotenv
├── test_cases.py            ← Automated test (6 use cases) — PYTHONUTF8=1 python test_cases.py
├── quick-demo-check.py      ← Full validation script (7 checks รวม health)
├── CHANGELOG.md             ← Version history
├── PROJECT_SUMMARY.md       ← ไฟล์นี้
├── CLAUDE.md                ← Rules สำหรับ Claude Code
├── PRE-DEMO-CHECKLIST.md    ← Checklist 30 นาทีก่อน demo
├── DEMO-READINESS-REPORT.md ← สรุปผลการตรวจสอบ demo readiness
├── .env                     ← OPENROUTER_API_KEY, OPENROUTER_MODEL (ห้าม commit)
├── .env.example             ← Template
├── .gitignore               ← exclude: .env, venv/, backup/screenshots/
├── backup/
│   ├── demo-inputs.txt      ← copy-paste inputs ทั้ง 6 cases พร้อมใช้
│   ├── demo-script.md       ← demo script พร้อม timing และ talking points
│   └── screenshots/         ← ภาพหน้าจอ backup (ไม่ commit)
└── docs/
    ├── poc-plan.md          ← แผน POC 2 คืน + session logs
    └── project-plan.md      ← แผน production Phase 0-4 (8 สัปดาห์)
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
PYTHONUTF8=1 python test_cases.py
PYTHONUTF8=1 python quick-demo-check.py
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

**กฎ versioning:** Minor bump (0.X.0) = agent/feature ใหม่ · Patch bump (0.0.X) = fix/tweak
**ทุก commit ต้อง bump version ใน `index.html` และเพิ่ม entry ใน `CHANGELOG.md`**

---

## UI Architecture (v0.3.x)

index.html ใช้ design system "The Silent Concierge":

```
Fixed Sidebar (256px)
  ├── Brand icon + "AI Assistant" + "INTERNAL POC"
  ├── Agent badge (แสดงหลังจาก agent ถูกเลือก)
  ├── Nav items × 6 (slide hover effect, Material Symbols icons)
  └── Footer: theme toggle + model pill + POC warning

Fixed Navbar (left: 256px, frosted glass)
  ├── App title + subtitle (agents list)
  └── Version tag (right)

Main area (margin-left: 256px)
  ├── output-wrap (scrollable, padding-bottom: 200px)
  │   ├── ai-accent-line (opacity 0→1 ระหว่าง streaming)
  │   └── output-area (plain text ระหว่าง stream → HTML หลัง done)
  └── Fixed input-footer (gradient fade + rounded input-box + send button)
```

**Markdown Rendering Flow:**
- ระหว่าง streaming: `output.textContent = outputText` (plain text)
- เมื่อ `done` event: `output.innerHTML = marked.parse(outputText)` → switch เป็น HTML

---

## Known Issues & Quirks

| ปัญหา | วิธีแก้ |
|---|---|
| Reasoning models (minimax, deepseek-r1) return `content=None` | Orchestrator ต้องใช้ `max_tokens ≥ 1024` |
| Windows terminal แสดงภาษาไทยแตก | prefix ด้วย `PYTHONUTF8=1` ทุกครั้ง |
| Model name ใน sidebar ไม่ตรง | ดึงจาก `/api/health` อัตโนมัติตอนโหลดหน้า |
| marked.js ต้องการ internet | โหลดจาก CDN — ถ้า offline จะ fallback เป็น plain text |

---

## สิ่งที่ POC นี้ไม่มี (ต้องบอกหัวหน้าตรงๆ)

- ❌ Login / Authentication
- ❌ เชื่อมต่อไฟล์บนเครื่อง (MCP)
- ❌ บันทึกประวัติการใช้งาน
- ❌ Database
- ❌ LangGraph (ใช้ direct API call แทน)

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
4. ทุกครั้งที่แก้ `index.html` → รัน `frontend-developer`
5. ก่อน demo → รัน `security-checker` แล้วตามด้วย `demo-preparer`
6. ท้ายทุก session → รัน `project-documenter` อัปเดต `docs/poc-plan.md`
7. **ทุก commit** → bump version ใน `index.html` + เพิ่ม entry ใน `CHANGELOG.md`
