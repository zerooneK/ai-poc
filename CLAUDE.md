# CLAUDE.md — Internal AI Assistant

## 🛠 คำสั่งที่ใช้บ่อย
- **รันระบบ:** `./start.sh` (Flask บน http://localhost:5000)
- **รันเทส Smoke (Phase 0):** `./venv/bin/python3 smoke_test_phase0.py`
- **รันเทส Use Cases:** `PYTHONUTF8=1 ./venv/bin/python3 test_cases.py`
- **Setup ครั้งแรก:** `bash setup.sh`

## 🏗 โครงสร้างโฟลเดอร์ (v0.12.0+)
- `app.py`: Flask Routes
- `core/`: Orchestrator, Factory, Shared State, Utils
- `agents/`: โมดูล Agent แต่ละแผนก (HR, Accounting, Manager, PM, Chat)
- `prompts/`: System Prompts (.md files)
- `workspace/`: พื้นที่เก็บเอกสารจริงที่สร้างเสร็จแล้ว
- `temp/`: พื้นที่เก็บ Draft เอกสารที่รอการยืนยัน
- `.claude/agents/`: คู่มือสำหรับ AI Assistant (Context Files)

## 📜 กฎเหล็ก (Mandatory Rules)
1.  **ภาษา:** AI Output + UI ต้องเป็นภาษาไทย 100%
2.  **วันที่:** ใช้ พ.ศ. (ปัจจุบัน 2569)
3.  **Disclaimer:** ท้ายเอกสารต้องมีคำเตือนเรื่อง AI Draft เสมอ
4.  **ไฟล์:** ชื่อไฟล์ต้องเป็น `english_snake_case.ext` ห้ามมีภาษาไทยในชื่อไฟล์
5.  **ความปลอดภัย:** ห้ามอ่าน/แก้ไขไฟล์นอก `workspace/` และห้ามแตะไฟล์ `.env` โดยตรง
6.  **Versioning:** ทุก commit ต้อง bump version ใน `index.html` + `CHANGELOG.md`
7.  **Documentation:** หลังงานเสร็จ ต้องอัปเดตเอกสาร (PROJECT_SUMMARY, CLAUDE.md, GEMINI.md) ให้ sync กัน

## 🔍 ลำดับการ Review ก่อน Commit (Mandatory Review Order)

ทุกครั้งที่มีการแก้ไขโค้ด ให้รัน subagent ตามลำดับนี้ก่อน commit เสมอ:

| ลำดับ | Subagent | Trigger |
|---|---|---|
| 1 | `backend-python-reviewer` | **ทุกครั้ง** ที่แก้ `app.py`, `core/`, `agents/`, `db.py`, `converter.py`, `mcp_server.py` |
| 2 | `python-reviewer` | แก้ไฟล์ `.py` ใดๆ นอกจากข้อ 1 (เช่น test scripts) |
| 3 | `ui-ux-reviewer` | แก้ `index.html` หรือ `history.html` |
| 4 | `security-checker` | ก่อน demo ทุกครั้ง หรือเมื่อแก้ `.env` / API config |
| 5 | `db-checker` | แก้ `db.py` หรือ `converter.py` |

> **กฎ:** ห้าม commit ถ้า `backend-python-reviewer` ยังไม่ผ่าน เมื่อมีการแก้ backend

## 📝 รูปแบบการ Commit (Message Format)
`vX.X.X — [fix/feature/refactor/docs]: <คำอธิบายภาษาไทยหรืออังกฤษ>`
*(ห้ามลืม bump version และ commit ในขั้นตอนเดียวกัน)*
