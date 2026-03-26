# Project Summary — Internal AI Assistant POC
> ไฟล์นี้ใช้เพื่อให้ AI เข้าใจภาพรวมทั้งโปรเจกต์อย่างรวดเร็ว

---

## โปรเจกต์คืออะไร

**Internal AI Assistant Platform** — ระบบ AI สำหรับพนักงานภายในบริษัทไทย
พนักงานพิมพ์งานเป็นภาษาไทย → AI เลือก Agent ที่เหมาะสม → สร้างเอกสาร (Draft) → User ยืนยัน → บันทึกเป็นไฟล์จริงในระบบ

- **Version ปัจจุบัน:** v0.12.0 (Major Refactoring)
- **สถานะ:** Prototype Ready (Verified by Smoke Tests)

---

## สถาปัตยกรรมใหม่ (Modular Architecture)

เพื่อให้ระบบบำรุงรักษาและขยายตัวได้ง่าย เราได้แยกส่วนประกอบออกดังนี้:

1.  **`app.py`**: Entry point หลักของ Flask จัดการ API Routes และ Request/Response flow
2.  **`core/`**: หัวใจของระบบ
    *   `orchestrator.py`: วิเคราะห์งานและเลือก Agent
    *   `agent_factory.py`: จัดการการสร้างและเรียกใช้ Agent Objects
    *   `shared.py`: เก็บสถานะส่วนกลาง (OpenAI Client, Workspace Path, Event Bus)
    *   `utils.py`: ฟังก์ชันสนับสนุน เช่น `load_prompt` และ `execute_tool`
3.  **`agents/`**: โมดูล Agent เฉพาะทาง
    *   `base_agent.py`: คลาสแม่ที่มี Logic การเรียก LLM และ Streaming
    *   `hr_agent.py`, `accounting_agent.py`, `manager_agent.py`, `pm_agent.py`, `chat_agent.py`
4.  **`prompts/`**: แหล่งเก็บ System Prompts แยกเป็นไฟล์ `.md` เพื่อให้ทำ Prompt Engineering ได้สะดวก

---

## เทคโนโลยีหลัก

- **Backend:** Flask (Python 3.11)
- **AI:** OpenRouter API (Claude 3.5 Sonnet / 4.5)
- **Frontend:** Vanilla HTML/JS/CSS (Silent Concierge Design)
- **Persistence:** SQLite (db.py) + Workspace Filesystem (MCP Server)
- **Streaming:** SSE (Server-Sent Events) พร้อมระบบ `format_sse` เพื่อความเสถียร

---

## กฎสำคัญในการพัฒนา (Strict Rules)

1.  **ภาษา:** ทุกอย่างที่ User เห็นต้องเป็น **ภาษาไทย**
2.  **ชื่อไฟล์:** ไฟล์ใน workspace ต้องเป็น **English snake_case** เท่านั้น ห้ามมีภาษาไทย
3.  **ความปลอดภัย:** ตรวจสอบ Path ผ่าน `_is_allowed_workspace_path` เสมอ
4.  **Version Control:** Bump version ทุกครั้งที่มีการแก้โค้ด และบันทึกลง CHANGELOG.md
5.  **Modular:** ห้ามใส่ Business Logic ยาวๆ ใน `app.py` ให้แยกเป็น Agent หรือ Core โมดูลเสมอ
