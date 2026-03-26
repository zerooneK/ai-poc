# Plan: Friendly Conversation Mode
**Version target:** v0.11.0 (Minor bump — new agent route + UX overhaul)
**Status:** Planned — not yet implemented
**Created:** 2026-03-25
**Depends on:** v0.10.0 (web_search) — can be done independently but scheduled after

---

## Problem
ระบบปัจจุบันรู้สึกเหมือน "สั่งงานหุ่นยนต์" ไม่ใช่ "คุยกับ AI Assistant"
- ทุกข้อความถูก route ไปหา specialist agent ทันที
- ไม่มี mode สำหรับคำถามทั่วไป การทักทาย หรือการสนทนา
- Agent ออก document ทันทีโดยไม่ acknowledge ผู้ใช้ก่อน
- Tone เป็น directive มาก ("สร้างเอกสาร... ทันที")

## Goal
ให้ระบบรู้สึกเหมือนคุยกับ ChatGPT/Gemini — warm, conversational, ตอบสนองต่อบริบท
ยังคงทำงานเอกสารได้ครบ แต่ tone และ flow เป็นธรรมชาติขึ้น

---

## Three Changes (เรียงตาม impact)

### Change 1 — เพิ่ม `chat` route ใน Orchestrator (impact สูงสุด)
### Change 2 — Agent acknowledge ก่อน execute (impact กลาง)
### Change 3 — Soften tone ใน system prompts ทุกตัว (impact เล็กน้อย)

---

## Implementation Steps

---

### CHANGE 1: Orchestrator `chat` route

#### Step 1.1 — อัปเดต `ORCHESTRATOR_PROMPT`
**ไฟล์:** `app.py`
**ตำแหน่ง:** `ORCHESTRATOR_PROMPT` string (บรรทัด ~118)

เพิ่ม `chat` เป็น agent ที่ valid:
```
ตอบกลับด้วย JSON เท่านั้น ห้ามมีข้อความอื่น:
{"agent": "hr", "reason": "เหตุผลสั้นๆ"}
{"agent": "accounting", "reason": "เหตุผลสั้นๆ"}
{"agent": "manager", "reason": "เหตุผลสั้นๆ"}
{"agent": "pm", "reason": "เหตุผลสั้นๆ"}
{"agent": "chat", "reason": "เหตุผลสั้นๆ"}    ← เพิ่ม
```

เพิ่มหมวด `chat` ใน routing guidelines:
```
Chat Agent เหมาะกับ:
- การทักทาย สวัสดี ขอบคุณ
- คำถามทั่วไปที่ไม่ใช่งานเอกสาร เช่น "คุณทำอะไรได้บ้าง" "อธิบายให้หน่อย"
- ขอคำชี้แจงหรือถามต่อจากงานที่ทำไปแล้ว
- ข้อความที่ไม่ชัดเจนว่าต้องการ HR / Accounting / Manager / PM
- การสนทนาทั่วไปที่ไม่ต้องการสร้างเอกสาร
```

#### Step 1.2 — เพิ่ม `CHAT_PROMPT` system prompt
**ไฟล์:** `app.py`
**ตำแหน่ง:** หลัง `MANAGER_PROMPT` ก่อน `MCP_TOOLS`

```python
CHAT_PROMPT = """
คุณคือ AI Assistant ภายในบริษัทที่ฉลาด เป็นมิตร และพร้อมช่วยเหลือเสมอ
คุยกับผู้ใช้อย่างเป็นธรรมชาติ อบอุ่น และกระชับ ไม่ verbose เกินไป

สิ่งที่คุณทำได้:
- ตอบคำถามทั่วไป ให้ข้อมูล อธิบายแนวคิด
- แนะนำว่าระบบทำอะไรได้บ้าง (HR เอกสาร / Accounting / คำแนะนำผู้จัดการ / PM งานหลายส่วน)
- สนทนาต่อยอดจากงานที่ทำไปแล้ว
- ช่วย brainstorm ก่อนที่ผู้ใช้จะสั่งงานจริง

แนวทาง:
- ใช้ภาษาไทยที่อ่านง่าย เป็นกันเอง ไม่เป็นทางการเกินไป
- ถ้าผู้ใช้ถามอะไรที่ควรส่งให้ specialist agent ให้แนะนำ เช่น
  "ถ้าต้องการสร้างสัญญาจ้างจริงๆ ลองบอกรายละเอียดได้เลยนะครับ"
- ไม่ต้องสร้างเอกสาร ไม่ต้องใช้ format เป็นทางการ
- ตอบสั้นพอดี ไม่ยาวจนน่าเบื่อ
"""
```

#### Step 1.3 — เพิ่ม `chat` branch ใน routing
**ไฟล์:** `app.py`
**ตำแหน่ง:** ใน `generate()` function ส่วน `else:` (single-agent path) หลัง `elif agent == 'accounting':`

```python
elif agent == 'chat':
    system_prompt = CHAT_PROMPT
    agent_label = 'Assistant'
    agent_max_tokens = 1000
```

#### Step 1.4 — เพิ่ม `chat` branch ใน `handle_revise()`
**ไฟล์:** `app.py`
**ตำแหน่ง:** ต้น `handle_revise()` function

```python
elif pending_agent == 'chat':
    system_prompt = CHAT_PROMPT
    agent_label = 'Assistant'
    max_tokens = 1000
```

#### Step 1.5 — อัปเดต frontend badge สำหรับ `chat` agent
**ไฟล์:** `index.html`
**ตำแหน่ง:** ส่วนที่ handle `type: 'agent'` event และ render badge

เพิ่ม case สำหรับ `chat`:
```javascript
// ในฟังก์ชัน _getAgentBadge หรือ switch ที่ handle agent event
case 'chat':
  return { label: 'Assistant', color: 'var(--secondary)' };
```

---

### CHANGE 2: Agent acknowledge ก่อน execute

เป้าหมาย: agent พูด 1 ประโยคสั้นๆ ก่อน output เอกสาร
รู้สึกเหมือนคนรับงานแล้วบอก "เข้าใจแล้วครับ กำลังทำให้นะครับ"

#### Step 2.1 — อัปเดต `HR_PROMPT`
**ไฟล์:** `app.py`

เพิ่มใน HR_PROMPT หลังส่วน `การใช้ list_files และ read_file`:
```
สไตล์การตอบ:
- เริ่มด้วยการ acknowledge งานสั้นๆ 1 ประโยค ก่อน output เอกสาร
  ตัวอย่าง: "รับทราบครับ จะจัดทำสัญญาจ้างให้เลยนะครับ"
           "เข้าใจแล้วครับ กำลังร่าง Job Description ให้"
- ถ้างานไม่ชัดเจน ให้ถามก่อน อย่าสมมติข้อมูลสำคัญเช่น ชื่อ วันที่ เงินเดือน
- หลัง output เอกสาร อาจถามสั้นๆ ว่า "มีอะไรอยากปรับเพิ่มเติมไหมครับ?"
```

#### Step 2.2 — อัปเดต `ACCOUNTING_PROMPT`
**ไฟล์:** `app.py`

เพิ่มส่วนเดียวกัน:
```
สไตล์การตอบ:
- เริ่มด้วยการ acknowledge งานสั้นๆ 1 ประโยค ก่อน output เอกสาร
  ตัวอย่าง: "รับทราบครับ จะออก Invoice ให้นะครับ"
           "เข้าใจแล้วครับ กำลังจัดทำงบประมาณให้"
- ถ้าข้อมูลตัวเลขไม่ครบ ให้ถามก่อน อย่าใส่ตัวเลขสมมติในเอกสาร
- หลัง output อาจถามว่า "มีรายการไหนอยากเพิ่มหรือปรับไหมครับ?"
```

#### Step 2.3 — อัปเดต `MANAGER_PROMPT`
**ไฟล์:** `app.py`

เพิ่มส่วนเดียวกัน:
```
สไตล์การตอบ:
- เริ่มด้วยการ acknowledge สั้นๆ ก่อนให้คำแนะนำ
  ตัวอย่าง: "เข้าใจสถานการณ์แล้วครับ มีข้อเสนอแนะดังนี้ครับ"
- ถ้าบริบทไม่ชัดเจน ให้ถามก่อน เช่น ขนาดทีม ประเด็นหลักที่กังวล
- หลัง output ถามสั้นๆ ว่า "มีประเด็นไหนอยากขยายความเพิ่มเติมไหมครับ?"
```

---

### CHANGE 3: Soften tone ใน system prompts

เปลี่ยน language จาก directive เป็น collaborative

#### Step 3.1 — HR_PROMPT
| เดิม | ใหม่ |
|---|---|
| `สร้างเอกสาร HR ที่ถูกต้อง เป็นมืออาชีพ` | `ช่วยจัดทำเอกสาร HR ที่ถูกต้อง เป็นมืออาชีพ` |
| `ถ้าผู้ใช้ขอสร้างเอกสารใหม่ ... ให้สร้างจากข้อมูลในคำขอทันที` | `ถ้าผู้ใช้ขอสร้างเอกสารใหม่ ... ให้เริ่มจัดทำจากข้อมูลในคำขอได้เลย` |

#### Step 3.2 — ACCOUNTING_PROMPT
| เดิม | ใหม่ |
|---|---|
| `สร้างเอกสารการเงินที่ถูกต้อง` | `ช่วยจัดทำเอกสารการเงินที่ถูกต้อง` |

#### Step 3.3 — MANAGER_PROMPT
| เดิม | ใหม่ |
|---|---|
| `ให้คำแนะนำที่นำไปปฏิบัติได้จริงภายใน 48 ชั่วโมง` | `ให้คำแนะนำที่นำไปปฏิบัติได้จริง เน้นสิ่งที่ทำได้ใน 48 ชั่วโมงแรก` |

#### Step 3.4 — ORCHESTRATOR_PROMPT
เพิ่มบรรทัดท้าย:
```
หมายเหตุ: ถ้าไม่แน่ใจว่า agent ไหนเหมาะ ให้เลือก chat ก่อนเสมอ
อย่า assume ว่าทุกข้อความต้องสร้างเอกสาร
```

---

## File Impact Summary

| ไฟล์ | สิ่งที่เปลี่ยน |
|---|---|
| `app.py` | `ORCHESTRATOR_PROMPT` เพิ่ม chat route + guidelines, `CHAT_PROMPT` ใหม่, `HR_PROMPT` / `ACCOUNTING_PROMPT` / `MANAGER_PROMPT` เพิ่ม acknowledge style + soften tone, routing branch เพิ่ม `chat`, `handle_revise()` เพิ่ม `chat` case |
| `index.html` | badge สำหรับ `chat` agent, version bump → v0.11.0 |
| `CLAUDE.md` | version history |
| `CHANGELOG.md` | v0.11.0 entry |
| `PROJECT_SUMMARY.md` | Agents table เพิ่ม Chat Agent |
| `docs/poc-plan.md` | progress update |

---

## UX Flow After This Change

**ก่อน (ปัจจุบัน):**
```
User: "สวัสดีครับ"
→ Orchestrator route → hr (หรือ error / weird output)

User: "ช่วยทำสัญญาจ้างให้หน่อย"
→ HR Agent → [document dump ทันที]
```

**หลัง (v0.11.0):**
```
User: "สวัสดีครับ"
→ Orchestrator route → chat
→ Assistant: "สวัสดีครับ! มีอะไรให้ช่วยไหมครับ? ระบบนี้ช่วยจัดทำเอกสาร HR สัญญาจ้าง Invoice หรือให้คำแนะนำด้านการบริหารทีมได้นะครับ"

User: "ช่วยทำสัญญาจ้างให้หน่อย"
→ HR Agent: "รับทราบครับ จะจัดทำสัญญาจ้างให้นะครับ"
→ [document output]
→ "มีอะไรอยากปรับเพิ่มเติมไหมครับ?"

User: "คุณทำอะไรได้บ้าง"
→ chat → อธิบาย capabilities แบบ friendly ไม่ใช่ list ยาว

User: "ขอบคุณครับ"
→ chat → "ยินดีครับ! มีอะไรอีกไหมครับ?"
```

---

## Risks & Mitigations

| ความเสี่ยง | ระดับ | แนวทางแก้ |
|---|---|---|
| Orchestrator route งาน HR/Accounting ผิดไป chat | กลาง | guidelines ชัดเจน + ใช้ "ถ้าไม่แน่ใจ ให้ chat" เฉพาะกรณีกำกวมจริงๆ |
| Agent acknowledge ยาวเกินไปก่อน document | ต่ำ | prompt จำกัด "1 ประโยค" ชัดเจน |
| Chat agent ตอบสั้นเกิน / ยาวเกิน | ต่ำ | `max_tokens=1000` + prompt "กระชับ ไม่ verbose" |
| `handle_revise()` ไม่มี `chat` case → crash | สูง | เพิ่ม `elif pending_agent == 'chat'` (Step 1.4) — ต้องไม่ลืม |
| test_cases.py อาจ fail เพราะ routing เปลี่ยน | กลาง | อัปเดต test_cases.py ให้รวม chat routing test |

---

## Test Cases ที่ต้องเพิ่มใน `test_cases.py`

```python
# Chat routing
{"input": "สวัสดีครับ", "expected_agent": "chat"},
{"input": "คุณทำอะไรได้บ้าง", "expected_agent": "chat"},
{"input": "ขอบคุณครับ", "expected_agent": "chat"},
{"input": "ช่วยอธิบายให้หน่อย", "expected_agent": "chat"},
# ยังต้อง route ถูกต้อง
{"input": "ทำสัญญาจ้างให้หน่อย", "expected_agent": "hr"},
{"input": "ออก invoice ให้หน่อย", "expected_agent": "accounting"},
```

---

## Out of Scope (ไม่ทำในรอบนี้)
- Memory เฉพาะ chat session (ใช้ conversation_history ที่มีอยู่แล้ว)
- Typing "คุณกำลังพิมพ์..." indicator สำหรับ chat (มีอยู่แล้วสำหรับทุก agent)
- Persona / ชื่อ AI assistant
- Emoji ใน responses

---

## Estimated Complexity
**ขนาดงาน:** เล็ก–กลาง
- app.py แก้ 5 จุด (orchestrator prompt, chat prompt ใหม่, 3 agent prompts, routing branch, handle_revise)
- index.html แก้ 1 จุด (badge) + version bump
- ไม่มี DB change, ไม่มี new endpoint, ไม่มี new file

**ความเสี่ยงต่อ stability:** ต่ำ–กลาง
- เพิ่ม route ใหม่ ไม่กระทบ route เดิม
- ความเสี่ยงหลักคือ Orchestrator route ผิด — แก้ด้วย prompt ที่ชัดเจน
