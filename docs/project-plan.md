# Internal AI Agent Platform — Project Plan

> ระบบ AI Assistant สำหรับพนักงานภายในบริษัท ที่ทุกตำแหน่งเข้าถึงและใช้งานได้ง่าย  
> โดย Orchestrator จะเลือก Agent ที่เหมาะสมกับงานของแต่ละแผนกโดยอัตโนมัติ

---

## Vision

พนักงานทุกคนสามารถบอกสิ่งที่อยากทำเป็นภาษาธรรมดา แล้วให้ระบบ AI ทำงานให้จนเสร็จ  
โดยไม่ต้องรู้เรื่อง AI, prompt engineering, หรือเทคโนโลยีใดๆ

---

## Tech Stack

### POC/Prototype (ทำแล้ว — v0.11.0)

| Layer | Technology |
|---|---|
| Frontend | index.html ไฟล์เดียว — "The Silent Concierge" UI, chat bubbles, confirmation flow, workspace picker modal, format selector popup, file panel |
| Backend | Python 3.11 + Flask + flask-cors |
| AI Provider | OpenRouter API via OpenAI SDK |
| Streaming | SSE (Server-Sent Events) |
| MCP Server | FastMCP (mcp_server.py) — 5 filesystem tools |
| File Watching | watchdog (Python) — real-time file panel updates |

### Production (แผนระยะถัดไป)

| Layer | Technology | เหตุผล |
|---|---|---|
| Frontend | React + Vite + TypeScript | เร็ว, type-safe, ecosystem ใหญ่ |
| Styling | Tailwind CSS | ทำ UI สวยได้เร็ว |
| Backend | Python + Flask | ควบคุมได้เต็มที่, ทีมคุ้นเคย |
| AI Orchestration | LangGraph | State machine ที่ชัดเจน, debug ง่าย |
| AI Model | Anthropic Claude (claude-sonnet-4-5) | ภาษาไทยดี, reasoning แม่น |
| File Access | MCP Filesystem Server | เข้าถึงไฟล์บนเครื่อง user อย่างปลอดภัย |
| Realtime | SSE (Server-Sent Events) | streaming progress กลับมา UI |
| Database | SQLite → PostgreSQL | เริ่มง่าย ขยายได้ |
| Deployment | Docker + Nginx | deploy บน Company Server |

---

## Architecture Overview

```
Local Network บริษัท
────────────────────────────────────────────────────────────────
เครื่อง User                          Company Server
┌──────────────────────┐            ┌─────────────────────────┐
│ Browser              │◄──SSE──────│ Flask API               │
│ (React Web UI)       │────REST───►│ ├── /api/chat           │
│                      │            │ ├── /api/stream          │
│ MCP Filesystem Server│◄──MCP──────│ ├── /api/history         │
│ (Node.js, local)     │            │ └── /api/download        │
│ └── /folder/งาน     │            │                         │
└──────────────────────┘            │ LangGraph Engine        │
                                    │ ├── Orchestrator         │
                                    │ ├── HR Agent             │
                                    │ ├── Accounting Agent     │
                                    │ └── Manager Agent (v2)   │
                                    │                         │
                                    │ MCP Client              │
                                    │                         │
                                    │ SQLite Database         │
                                    │ ├── users               │
                                    │ ├── jobs                │
                                    │ └── results             │
                                    └─────────────────────────┘
```

---

## Agent Roster

### ✅ พิสูจน์แล้วใน POC (v0.4.20)

| Agent | แผนก | ความสามารถหลัก | max_tokens |
|---|---|---|---|
| **Orchestrator** | ทุกแผนก | วิเคราะห์งาน + เลือก Agent ที่เหมาะสม (ตอบ JSON) | 1,024 |
| **HR Agent** | Human Resources | สัญญาจ้าง, JD, HR policy, อีเมลแจ้งนโยบาย | 7,500 |
| **Accounting Agent** | บัญชี/การเงิน | Invoice (+ VAT 7%), Expense Report, งบประมาณ | 6,000 |
| **Manager Advisor** | ผู้บริหาร/Team Lead | Feedback script, headcount, budget, ลำดับความสำคัญ | 8,000 |
| **PM Agent** | ทุกแผนก | งานหลายแผนก → แยก subtasks → route + delegate → สร้างไฟล์ผ่าน MCP | 8,000 |

> **หมายเหตุ:** Manager Advisor และ PM Agent ถูก implement และทดสอบแล้วใน POC ไม่จำเป็นต้องรอ Phase 3+

### Phase 4+ (เพิ่มเติมในอนาคต)

| Agent | แผนก | ความสามารถหลัก |
|---|---|---|
| **Legal Agent** | กฎหมาย | ร่างสัญญา, compliance checklist |
| **IT Agent** | IT | troubleshoot, คู่มือการใช้งาน |
| **Marketing Agent** | การตลาด | content, แผนการตลาด, copywriting |

---

## แผนการพัฒนา

---

## Phase 0 — Preparation
**ระยะเวลา:** 1 สัปดาห์  
**เป้าหมาย:** เตรียม environment และ requirement ให้พร้อมก่อน build จริง

### สิ่งที่ต้องทำ

- [ ] ติดตั้ง environment: Python 3.11+, Node.js, Docker บน development machine
- [ ] สร้าง Anthropic API Key และทดสอบเรียก Claude API ได้
- [ ] รวบรวม template เอกสารที่ HR และ Accounting ใช้จริง (สัญญาจ้าง, invoice, JD)
- [ ] สัมภาษณ์ HR และ Accounting อย่างน้อยแผนกละ 1 คน — งานอะไรที่ทำซ้ำบ่อยที่สุด
- [ ] กำหนด folder structure บนเครื่อง user ที่จะให้ MCP เข้าถึง
- [ ] ออกแบบ database schema เบื้องต้น

### ผลลัพธ์ที่ต้องได้

- Development environment พร้อมใช้งาน
- รายการ use cases อย่างน้อย 5 อย่างต่อ Agent พร้อม template เอกสารจริง
- โครงสร้างโปรเจกต์ที่ทุกคนในทีมเห็นตรงกัน

### วัดผลอย่างไร

- [ ] `python -c "import anthropic"` ไม่ error
- [ ] Claude API ตอบสนองได้ใน < 5 วินาที
- [ ] มี use case document ที่ HR และ Accounting sign off แล้ว

---

## Phase 1 — Backend Core (MVP)
**ระยะเวลา:** 2-3 สัปดาห์  
**เป้าหมาย:** ระบบทำงานได้จริงใน terminal ก่อน — ยังไม่มี UI

### สิ่งที่ต้องทำ

**1.1 Flask App Skeleton**
- [ ] สร้างโครงสร้างโปรเจกต์ Flask
- [ ] กำหนด API routes: `/api/chat`, `/api/stream`, `/api/history`, `/api/download`
- [ ] ตั้งค่า CORS สำหรับ React dev server
- [x] สร้าง SQLite database + schema: jobs, saved_files (v0.5.0 — db.py)

**1.2 LangGraph — Orchestrator**
- [ ] สร้าง `FlowState` (shared state ระหว่าง nodes)
- [ ] สร้าง Orchestrator node ที่วิเคราะห์งานและ route ไปหา Agent ที่ถูกต้อง
- [ ] เขียน system prompt ของ Orchestrator ที่เข้าใจบริบทบริษัท
- [ ] ทดสอบ routing: ส่งงาน HR → ได้ HR Agent, ส่งงานบัญชี → ได้ Accounting Agent

**1.3 HR Agent**
- [ ] สร้าง HR Agent node ใน LangGraph
- [ ] เขียน system prompt ที่รู้เรื่อง HR policy บริษัท
- [ ] tools: `read_file()`, `create_document()`, `search_policy()`
- [ ] ทดสอบ: ร่างสัญญาจ้างได้ถูกต้อง

**1.4 Accounting Agent**
- [ ] สร้าง Accounting Agent node ใน LangGraph
- [ ] เขียน system prompt ที่รู้เรื่องระบบบัญชีบริษัท
- [ ] tools: `read_file()`, `create_document()`, `calculate()`, `parse_excel()`
- [ ] ทดสอบ: สร้าง invoice ได้ถูกต้อง, อ่านและสรุป Excel ได้

**1.5 MCP Integration**
- [ ] ติดตั้งและทดสอบ `@modelcontextprotocol/server-filesystem`
- [ ] สร้าง MCP Client ใน Flask ที่เชื่อมกับ MCP server บนเครื่อง user
- [ ] ทดสอบ: Agent อ่านไฟล์จาก directory ที่กำหนดได้

**1.6 SSE Streaming**
- [ ] implement `/api/stream` endpoint ที่ส่ง progress กลับแบบ real-time
- [ ] กำหนด event types: `agent_selected`, `thinking`, `tool_call`, `result`, `done`, `error`

### ผลลัพธ์ที่ต้องได้

สามารถส่ง HTTP request หา Flask และได้ผลลัพธ์ที่ถูกต้องจาก HR และ Accounting Agent  
พร้อม progress streaming ผ่าน SSE

### วัดผลอย่างไร

- [ ] Orchestrator routing accuracy ≥ 95% (ทดสอบ 20 cases)
- [ ] HR Agent สร้างสัญญาจ้างได้ถูกต้อง ผ่านการตรวจจาก HR จริง
- [ ] Accounting Agent สร้าง invoice และสรุป Excel ได้ถูกต้อง ผ่านการตรวจจาก Accounting จริง
- [ ] Response time รวม (รับงาน → ได้ผลลัพธ์) ≤ 60 วินาทีสำหรับงานทั่วไป
- [ ] MCP อ่านไฟล์จาก user directory ได้โดยไม่ error
- [ ] SSE ส่ง progress events ได้ครบทุก step

---

## Phase 2 — Frontend (MVP UI)
**ระยะเวลา:** 2 สัปดาห์  
**เป้าหมาย:** พนักงานบริษัทใช้งานได้จริงผ่าน Browser

### สิ่งที่ต้องทำ

**2.1 React App Setup**
- [ ] สร้างโปรเจกต์ด้วย Vite + TypeScript + Tailwind CSS
- [ ] กำหนด folder structure: components, pages, hooks, stores
- [ ] สร้าง Zustand store สำหรับ job state และ message history

**2.2 หน้าหลัก — Chat Interface**
- [ ] Input box สำหรับพิมพ์งาน (รองรับภาษาไทย)
- [ ] ปุ่มแนบไฟล์ (ส่งไปยัง Flask upload endpoint)
- [ ] แสดง suggested prompts ตามแผนกของ user
- [ ] ปุ่ม "เริ่มทำงาน"

**2.3 Progress Display**
- [ ] แสดงสถานะ real-time ผ่าน SSE: "กำลังวิเคราะห์งาน...", "HR Agent กำลังร่างเอกสาร..."
- [ ] Progress bar หรือ step indicator
- [ ] ไม่แสดง technical detail ให้ user เห็น — แค่ภาษาที่เข้าใจง่าย

**2.4 ผลลัพธ์และ Download**
- [ ] แสดงผลลัพธ์ที่ได้ (preview สำหรับ text, ปุ่ม download สำหรับไฟล์)
- [ ] ปุ่ม download สำหรับ DOCX/PDF/Excel
- [ ] แสดง thumbnail หรือ preview ของเอกสาร

**2.5 MCP Connection UI**
- [ ] หน้าตั้งค่า: ให้ user กำหนด folder ที่อนุญาตให้เข้าถึง
- [ ] แสดงสถานะการเชื่อมต่อ MCP (connected/disconnected)
- [ ] คำแนะนำติดตั้ง MCP server สำหรับ user ใหม่

**2.6 ประวัติงาน**
- [ ] แสดงรายการงานที่ผ่านมา เรียงตามวันที่
- [ ] กดดูผลลัพธ์เก่าและ download ซ้ำได้
- [ ] filter ตามแผนก / Agent / วันที่

### ผลลัพธ์ที่ต้องได้

พนักงาน HR หรือ Accounting สามารถ:
1. เปิด browser → พิมพ์งาน → รอ → download ไฟล์ ได้ภายใน 2 นาที
2. กลับมาดูงานเก่าและ download ซ้ำได้

### วัดผลอย่างไร

- [ ] User ที่ไม่เคยใช้มาก่อนทำงานแรกสำเร็จได้ภายใน 5 นาทีโดยไม่มีคนช่วย
- [ ] ไม่มี error ที่ทำให้ user หยุดทำงานได้ใน happy path
- [ ] UI แสดงผลถูกต้องบน Chrome และ Edge (browser หลักของบริษัท)
- [ ] ทดสอบกับพนักงาน HR และ Accounting จริงอย่างน้อย 3 คน และได้ feedback เป็นบวก

---

## Phase 3 — Auth + Security + Stability
**ระยะเวลา:** 2 สัปดาห์  
**เป้าหมาย:** พร้อม deploy จริงอย่างปลอดภัย

### สิ่งที่ต้องทำ

**3.1 Authentication**
- [ ] Login ด้วย username/password (เชื่อมกับ Active Directory หรือ user table)
- [ ] JWT session management
- [ ] แยก workspace และประวัติงานตาม user
- [ ] กำหนด role: admin, manager, hr, accounting, general

**3.2 Authorization**
- [ ] กำหนดว่า role ไหนเข้าถึง Agent ไหนได้บ้าง
- [ ] Audit log: บันทึกว่าใครใช้งานอะไร เมื่อไหร่
- [ ] Rate limiting: จำกัดการใช้งาน API per user

**3.3 Security**
- [ ] MCP: จำกัด folder ที่ agent เข้าถึงได้อย่างเข้มงวด
- [ ] Sanitize input ก่อนส่งให้ AI
- [ ] ไม่ log ข้อมูลส่วนตัวหรือข้อมูลทางการเงินใน plain text
- [ ] HTTPS บน production

**3.4 Error Handling**
- [ ] Retry logic เมื่อ Claude API timeout
- [ ] แสดง error message ที่เข้าใจง่ายเมื่อมีปัญหา
- [ ] Fallback เมื่อ MCP ไม่ได้เชื่อมต่อ

**3.5 Deployment**
- [ ] สร้าง Dockerfile สำหรับ Flask backend
- [ ] สร้าง Docker Compose สำหรับ local dev
- [ ] ตั้งค่า Nginx reverse proxy
- [ ] deploy บน Company Server และทดสอบกับ network จริง

### ผลลัพธ์ที่ต้องได้

ระบบพร้อม production — มี auth, logging, error handling ครบ  
deploy บน Company Server แล้ว พนักงานเข้าถึงได้ผ่าน internal URL

### วัดผลอย่างไร

- [ ] ไม่มี unauthorized access — ทดสอบด้วย penetration test เบื้องต้น
- [ ] Audit log บันทึกทุก job ครบถ้วน
- [ ] Uptime ≥ 99% ใน 1 สัปดาห์แรกของ production
- [ ] Recovery จาก Claude API timeout ได้โดยอัตโนมัติ
- [ ] พนักงานทุกคนที่มี account login ได้และใช้งานได้ภายใน 1 วันหลัง deploy

---

## Phase 4 — Expand Agents + Feedback Loop
**ระยะเวลา:** ต่อเนื่อง (หลังจาก Phase 3 stable)  
**เป้าหมาย:** เพิ่ม Agent ใหม่ และปรับปรุงจาก feedback ผู้ใช้จริง

### สิ่งที่ต้องทำ

**4.1 Manager Agent**
- [ ] สร้าง Manager Agent: สรุปรายงาน, วิเคราะห์ผลการทำงาน, ร่าง agenda ประชุม
- [ ] tools: `summarize_report()`, `create_presentation_outline()`, `analyze_data()`

**4.2 Feedback System**
- [ ] ปุ่ม 👍 / 👎 หลังทุก job
- [ ] เก็บ feedback เพื่อปรับปรุง prompt และ Agent behavior
- [ ] Dashboard สำหรับ admin ดู usage stats และ satisfaction score

**4.3 ปรับปรุง Agent Quality**
- [ ] วิเคราะห์ cases ที่ได้ 👎 และแก้ prompt
- [ ] เพิ่ม few-shot examples จากงานจริงที่ผ่านแล้ว

**4.4 Agent ใหม่ตาม Priority**
- [ ] Legal Agent (ถ้ามีความต้องการ)
- [ ] IT Agent
- [ ] Marketing Agent

### ผลลัพธ์ที่ต้องได้

Manager Agent ใช้งานได้  
มีระบบ feedback และ dashboard สำหรับ monitor คุณภาพ

### วัดผลอย่างไร

- [ ] User satisfaction score (จาก 👍/👎) ≥ 85%
- [ ] Manager Agent ผ่านการ review จาก manager จริง ≥ 3 คน
- [ ] จำนวน active users เพิ่มขึ้น month-over-month
- [ ] Average jobs per user per week ≥ 3 (แสดงว่าใช้งานจริง ไม่ใช่แค่ลองแล้วเลิก)

---

## Timeline Summary

| Phase | ชื่อ | ระยะเวลา | Milestone |
|---|---|---|---|
| 0 | Preparation | 1 สัปดาห์ | Environment + Requirements พร้อม |
| 1 | Backend Core | 2-3 สัปดาห์ | API ทำงานได้, Agent ตอบถูกต้อง |
| 2 | Frontend MVP | 2 สัปดาห์ | พนักงานใช้งานผ่าน Browser ได้ |
| 3 | Auth + Deploy | 2 สัปดาห์ | Production-ready บน Company Server |
| 4 | Expand + Improve | ต่อเนื่อง | เพิ่ม Agent + ปรับปรุงคุณภาพ |

**รวม Time to MVP: ~7-8 สัปดาห์**

---

## API Cost Planning

### เป้าหมาย Budget
- พนักงาน: 30 คน
- Budget ceiling: $600-700 USD/เดือน
- Model: Claude Sonnet — $3/1M input tokens, $15/1M output tokens

### Token Usage จริงที่ต้องเข้าใจ

**System Prompt คือ overhead ที่เกิดทุก request**
```
Orchestrator system prompt:  ~300 tokens
Agent system prompt:         ~400 tokens
รวม overhead/job:            ~700 tokens (ก่อนนับ user input)
```

**MCP Tool Calls เพิ่ม Token ต่อครั้งที่เรียก**
```
Tool definition (บอก Claude ว่ามี tool อะไร):  ~200-500 tokens
Tool call request:                               ~100-200 tokens
Tool result (เนื้อหาไฟล์):                      ขึ้นกับขนาดไฟล์
```

**ขนาดไฟล์เมื่อแปลงเป็น Token**
```
Excel งบรายเดือน 50 แถว:       ~3,000-5,000 tokens
Excel งบรายปี 200+ แถว:         ~10,000-20,000 tokens
Excel หลาย sheet:               ~20,000-50,000 tokens
PDF สัญญา 3-5 หน้า:            ~4,000-8,000 tokens
PDF รายงานประจำปี 20 หน้า:     ~20,000-40,000 tokens
Word template สัญญา:            ~2,000-5,000 tokens
CSV รายชื่อพนักงาน 100 คน:     ~2,000-4,000 tokens
```

**Multi-turn conversation — token เพิ่มแบบสะสม**
```
รอบที่ 1: 1,000 tokens input
รอบที่ 2: 1,000 + 1,500 (history) = 2,500 tokens
รอบที่ 3: 2,500 + 1,500 (history) = 4,000 tokens
รอบที่ 4: 4,000 + 1,500 (history) = 5,500 tokens
1 งานที่คุย 4 รอบ = ~13,000 tokens input รวม
```

### Use Cases ที่เกิน 10,000 Tokens ได้ง่าย

| Use Case | Input | Output | รวม |
|---|---|---|---|
| แนบ Excel แล้วให้สรุป | ~5,000-8,000 | ~2,000 | ~10,000 |
| แก้สัญญาจ้างจากไฟล์เก่า + template | ~8,000 | ~4,000 | ~12,000 |
| วิเคราะห์งบการเงินรายปี (4 ไฟล์) | ~33,000 | ~5,200 | ~38,200 |
| ค้นหา policy จาก folder (3 ไฟล์) | ~25,500 | ~3,200 | ~28,700 |
| คุยต่อเนื่อง 4-5 รอบ | ~8,000-12,000 | ~6,000-8,000 | ~20,000 |

### การประมาณค่าใช้จ่าย (30 คน, 5 งาน/คน/วัน)

```
3,300 งาน/เดือน แบ่งตามประเภท:

งานง่าย — ไม่ใช้ MCP           40% → 1,320 งาน × 3,000 tokens
งานกลาง — MCP อ่าน 1-2 ไฟล์เล็ก 35% → 1,155 งาน × 13,500 tokens
งานหนัก — MCP อ่านหลายไฟล์ใหญ่  20% →   660 งาน × 38,000 tokens
งานหนักมาก — MCP อ่าน folder    5%  →   165 งาน × 80,000 tokens

รวม ~57,800,000 tokens/เดือน
Input 65%:  ~37,600,000 × $3/1M   = $112.8
Output 35%: ~20,200,000 × $15/1M  = $303.0
Base Case: ~$416/เดือน

เพิ่ม buffer 1.5x (retry, dev/test, peak usage):
Worst Case: ~$624/เดือน ← แทบจะชนเพดาน $600-700
```

### ⚠️ สิ่งที่ต้องทำเพื่อคุม Cost

```
1. ตั้ง token limit ต่อ job: max 50,000 tokens
   → ถ้าไฟล์ใหญ่เกิน แจ้ง user ก่อนดำเนินการ

2. เปิด Prompt Caching สำหรับ System Prompt
   → ประหยัดได้ ~60-80% ของ system prompt cost

3. เก็บ token log ทุก request ตั้งแต่วันแรก
   → Anthropic API return token count ทุก call
   → เก็บใน database เพื่อ monitor และ optimize

4. แจ้งหัวหน้าว่า $600-700 คือ ceiling
   → ตัวเลขจริงรู้ได้หลังใช้งาน 30 วันแรก
```

---

## Data Privacy & API Provider

### คำถามที่ IT หรือ Legal จะถามแน่นอน

> "ข้อมูลบริษัทส่งไป Anthropic ไหม? เก็บไว้ไหม? ใครเข้าถึงได้?"

### ตัวเลือก API Provider และระดับความปลอดภัย

| ตัวเลือก | ความปลอดภัย | ความยุ่งยาก | เหมาะกับ |
|---|---|---|---|
| **Anthropic API โดยตรง** | ดี — ไม่ train บน API data | น้อยสุด | POC และ Production ทั่วไป |
| **OpenRouter + ZDR** | ดีพอ — ไม่เก็บ prompt ถ้าเปิด ZDR | ปานกลาง | ถ้าต้องการ multi-model |
| **AWS Bedrock Claude** | สูงมาก — กำหนด region ได้ | มากกว่า | ถ้ามี data residency requirement |

### จุดสำคัญของแต่ละตัวเลือก

**Anthropic API โดยตรง (แนะนำสำหรับโปรเจกต์นี้)**
- Anthropic ระบุชัดว่าไม่ใช้ข้อมูล API เพื่อ train model
- ข้อมูลผ่าน server ของ Anthropic ที่ตั้งใน US
- ราคา $3/$15 per million tokens
- Setup ง่ายที่สุด ลด layer ที่ต้องอธิบาย

**OpenRouter + ZDR**
- ZDR = Zero Data Retention — prompt ไม่ถูกเก็บถ้าเปิด option
- มีเพียง metadata (token count, latency) เท่านั้นที่เก็บ
- ข้อมูลยังผ่าน server ใน US อยู่ดี
- เหมาะถ้าอยากทดลองหลาย model หรือต้องการ fallback
- **ไม่แนะนำสำหรับโปรเจกต์นี้** เพราะเพิ่ม layer โดยไม่จำเป็น

**AWS Bedrock Claude (ทางออกถ้า IT บล็อก)**
- ราคาเท่ากัน $3/$15 per million tokens
- Deploy ใน AWS region ที่กำหนดได้ เช่น ap-southeast-1 (Singapore)
- ข้อมูลไม่ออกนอก region
- เหมาะถ้าบริษัทมี data residency requirement หรือใช้ AWS อยู่แล้ว

### แนวทางที่แนะนำ

```
POC (ตอนนี้):
→ ใช้ Anthropic API โดยตรง
→ เตรียมคำตอบว่า "Anthropic ไม่ train บน API data"

Production:
→ ถามฝ่าย IT ก่อนว่ามี data residency requirement ไหม
→ ถ้าไม่มี: Anthropic API โดยตรงได้เลย
→ ถ้ามี: เปลี่ยนเป็น AWS Bedrock ที่ region Singapore
```

---

## Risk & Mitigation

| ความเสี่ยง | ระดับ | แนวทางแก้ |
|---|---|---|
| Claude API มี latency สูง | กลาง | ตั้ง timeout + retry, แสดง progress ให้ user เห็นว่ากำลังทำงาน |
| User ไม่ยอมติดตั้ง MCP server | สูง | สร้าง installer script ให้คลิกครั้งเดียว + fallback เป็น upload ไฟล์แทน |
| Agent ให้ข้อมูลผิด (hallucination) | สูง | ให้ผู้เชี่ยวชาญ review output ก่อน phase 3, เพิ่ม disclaimer ในเอกสาร |
| ข้อมูลบริษัทรั่วไหล | สูง | MCP จำกัด folder, ไม่ส่งข้อมูลออก internet, ใช้ API key ของบริษัทเอง |
| พนักงานไม่ adopt | กลาง | เลือก use case ที่ประหยัดเวลาได้ชัดเจน, ทำ onboarding session |
| ค่า API เกิน budget | กลาง | ตั้ง token limit ต่อ job, เปิด prompt caching, monitor token log ทุกวัน |
| IT บล็อก Anthropic API | กลาง | เตรียม option สำรองเป็น AWS Bedrock Singapore region |
| MCP พังบนเครื่อง user | สูง | สร้าง fallback เป็น file upload แทน, ทำ installer script ให้ง่ายที่สุด |
| Timeline ยาวกว่าแผนถ้าทำคนเดียว | สูง | 8 สัปดาห์ = full-time, ถ้าทำหลังเลิกงานคนเดียว = 16-20 สัปดาห์ จริงๆ ควรขอ dev เพิ่ม |

---

## Definition of Done (โดยรวม)

ระบบพร้อม production เมื่อ:

- [ ] พนักงาน HR และ Accounting ใช้งานได้โดยไม่ต้องมีคนช่วย
- [ ] ผลลัพธ์ที่ได้ผ่านการ review จากผู้เชี่ยวชาญแต่ละแผนกแล้ว
- [ ] ระบบ stable ไม่มี downtime ใน business hours
- [ ] มี auth, logging, และ error handling ครบ
- [ ] User satisfaction ≥ 85% จาก feedback จริง
