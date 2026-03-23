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
- app.py          — Flask server + Orchestrator + Agent logic
- index.html      — Web UI (dark/light toggle, Enter ส่ง, Shift+Enter ขึ้นบรรทัดใหม่)
- .env            — `OPENROUTER_API_KEY` และ `OPENROUTER_MODEL` (ห้าม commit)
- .env.example    — template สำหรับ setup ใหม่
- requirements.txt — flask, flask-cors, openai, python-dotenv
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
- Version ปัจจุบัน: **v0.3.0**

ประวัติ:
- v0.1.0 — initial POC (HR + Accounting agents, SSE streaming)
- v0.2.0 — Manager Advisor agent + timer counter + copy button
- v0.2.1 — fix Manager badge label/color, update sidebar agent list
- v0.2.2 — adopt semantic versioning scheme
- v0.2.3 — PROJECT_SUMMARY.md (AI context document)
- v0.3.0 — UI redesign "The Silent Concierge" (Navbar + Sidebar redesign, dark/light tokens, Material Symbols)

## Rules ที่ต้องทำตามเสมอ
- ภาษาไทยใน UI และ system prompts ทั้งหมด
- ทุก agent output ต้องมี disclaimer ว่าเป็น draft
- Error messages เป็นภาษาไทยที่ user เข้าใจ ไม่ใช่ technical
- ห้าม hardcode API key ใน code เด็ดขาด
- ก่อนเริ่มงานใหม่ทุกครั้ง อ่าน docs/poc-plan.md ก่อน

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

### At end of each work session
→ Run project-documenter to update docs/poc-plan.md