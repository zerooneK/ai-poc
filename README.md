# AI Assistant Internal POC

ภาษาไทย / English

## ไทย

### โปรเจกต์นี้คืออะไร
ระบบ AI ภายในบริษัทสำหรับช่วยร่างเอกสาร ตอบคำถาม และเลือก agent ให้เหมาะกับงานอัตโนมัติ เช่น HR, Accounting, Manager, PM และ Chat Agent

### โครงสร้างหลัก
- `app.py` : Flask backend และ SSE streaming
- `core/` : orchestration, shared state, utilities
- `agents/` : agent แต่ละประเภท
- `prompts/` : system prompts
- `workspace/` : ไฟล์ที่บันทึกแล้ว
- `temp/` : ไฟล์ draft ชั่วคราว
- `data/` : SQLite data
- `docs/` : เอกสารอธิบายระบบ

### วิธีเริ่มใช้งาน
1. ติดตั้งครั้งแรก

```bash
bash setup.sh
```

2. สร้างไฟล์ config

```bash
cp .env.example .env
```

3. ใส่ `OPENROUTER_API_KEY` ใน `.env`

4. รันเซิร์ฟเวอร์

```bash
./start.sh
```

5. เปิดใช้งานที่ `http://localhost:5000`

### คำสั่งทดสอบ

```bash
python smoke_test_phase0.py
python test_cases.py
python test_concurrency_pm.py --tc 1 2 3 4
python quick-demo-check.py
```

- `smoke_test_phase0.py` : เช็คระบบพื้นฐาน
- `test_cases.py` : ทดสอบ flow หลักของ agent
- `test_concurrency_pm.py` : ทดสอบงานพร้อมกัน
- `quick-demo-check.py` : เช็ค use cases สำหรับ demo

### Local Agent Mode (ทางเลือก)
ถ้าต้องการให้ AI จัดการไฟล์บน Windows โดยตรง:

```bash
python local_agent.py
```

จากนั้นหน้าเว็บจะเชื่อมกับ local workspace อัตโนมัติเมื่อ agent ทำงานอยู่ที่ port `7000`

### หมายเหตุสำคัญ
- ห้าม commit ไฟล์ `.env`
- แก้ค่าหลักใน `.env.example` ได้จากไฟล์ `.env`
- อ่านรายละเอียดเพิ่มได้ที่ `docs/MANUAL.md` และ `AGENTS.md`

### Troubleshooting / การแก้ปัญหาเบื้องต้น
- Server ไม่เริ่มทำงาน: ตรวจว่า `.env` มีอยู่จริง และมี `OPENROUTER_API_KEY`
- ติดตั้ง dependencies ไม่ผ่าน: รัน `bash setup.sh` ใหม่ และดู error ล่าสุดใน terminal
- เปิดเว็บไม่ได้ที่ `localhost:5000`: ตรวจว่ามี process อื่นใช้ port `5000` อยู่หรือไม่
- Local Agent ไม่ถูกตรวจพบ: รัน `python local_agent.py` และตรวจว่าใช้งาน port `7000`
- AI ไม่ตอบหรือ timeout: ลองเพิ่ม `OPENROUTER_TIMEOUT` และให้ `GUNICORN_TIMEOUT` มากกว่าค่านั้น

## English

### What this project is
This is an internal AI assistant prototype for drafting documents, answering questions, and routing work to the right agent automatically: HR, Accounting, Manager, PM, and Chat.

### Main structure
- `app.py`: Flask backend and SSE streaming
- `core/`: orchestration, shared state, utilities
- `agents/`: agent implementations
- `prompts/`: system prompts
- `workspace/`: saved output files
- `temp/`: temporary draft files
- `data/`: SQLite data
- `docs/`: deeper technical documentation

### Quick start
1. Run first-time setup

```bash
bash setup.sh
```

2. Create your config file

```bash
cp .env.example .env
```

3. Add your `OPENROUTER_API_KEY` to `.env`

4. Start the server

```bash
./start.sh
```

5. Open `http://localhost:5000`

### Test commands

```bash
python smoke_test_phase0.py
python test_cases.py
python test_concurrency_pm.py --tc 1 2 3 4
python quick-demo-check.py
```

- `smoke_test_phase0.py`: basic health and safety checks
- `test_cases.py`: main routed agent flows
- `test_concurrency_pm.py`: concurrency and workspace-switch tests
- `quick-demo-check.py`: fast demo validation

### Optional: Local Agent Mode
If you want the app to manage files directly on Windows:

```bash
python local_agent.py
```

When the local agent is running on port `7000`, the web app can switch to the local workspace flow automatically.

### Important notes
- Do not commit `.env`
- Main runtime settings are in `.env`
- For more detail, see `docs/MANUAL.md` and `AGENTS.md`

### Troubleshooting
- Server does not start: make sure `.env` exists and `OPENROUTER_API_KEY` is set
- Dependency install fails: run `bash setup.sh` again and check the latest terminal error
- `localhost:5000` does not open: check whether another process is already using port `5000`
- Local Agent is not detected: run `python local_agent.py` and confirm port `7000` is active
- AI replies time out: increase `OPENROUTER_TIMEOUT` and keep `GUNICORN_TIMEOUT` higher than that value
