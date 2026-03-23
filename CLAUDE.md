# AI POC — Internal AI Assistant

## โปรเจกต์นี้คืออะไร
Flask + Anthropic API สำหรับ demo ต่อหัวหน้า
Multi-agent: Orchestrator → HR Agent / Accounting Agent
Output: เอกสารภาษาไทย (สัญญาจ้าง, invoice, JD)

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