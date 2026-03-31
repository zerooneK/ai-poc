# PRE-DEMO CHECKLIST — Internal AI Assistant POC
**Demo Date:** 2026-03-23 (หรือตามกำหนด)
**Duration:** 7 นาที
**Version:** v0.12.2
**Status:** NEEDS ATTENTION (อ่านด้านล่าง)

---

## CRITICAL ISSUES FOUND

### 1. ⚠️ NO BACKUP SCREENSHOTS
**Status:** ❌ NOT READY
**Issue:** ไม่มีไฟล์ screenshot ใน `backup/screenshots/`
**Impact:** ถ้า internet หรือ API ล่ม จะไม่มี backup แสดง
**Fix Required:**
```bash
# ต้องรัน app และ capture screenshots สำหรับทุก use case:
# 1. HR — สัญญาจ้าง
# 2. HR — Job Description
# 3. HR — อีเมลนโยบาย WFH
# 4. Accounting — Invoice
# 5. Accounting — สรุปค่าใช้จ่าย
# 6. Manager — Feedback พนักงาน

# Save เป็น:
# - case1-hr-contract.png
# - case2-hr-jd.png
# - case3-hr-email.png
# - case4-accounting-invoice.png
# - case5-accounting-expense.png
# - case6-manager-feedback.png
```

### 2. ⚠️ MODEL CONFIGURATION
**Status:** ⚠️ CAUTION
**Current Model:** `minimax/minimax-m2.7` (ตาม .env)
**App Default:** `anthropic/claude-sonnet-4-5`
**Issue:** minimax model อาจให้ผลลัพธ์ไม่สม่ำเสมอ
**Recommendation:**
- ถ้าจะ demo ด้วย Claude Sonnet 4.5 → แก้ .env เป็น `OPENROUTER_MODEL=anthropic/claude-sonnet-4-5`
- ถ้าจะใช้ minimax → ทดสอบทุก case ให้แน่ใจว่า routing ถูกต้อง

---

## SYSTEM STATUS

### ✅ PASSED CHECKS

#### Environment
- ✅ Flask server สามารถรันได้ (`bash start.sh` หรือ `source venv/bin/activate && flask run --host=0.0.0.0`)
- ✅ Dependencies ครบ (flask, flask-cors, openai, python-dotenv, mcp, watchdog, ddgs)
- ✅ .env file มี API key configured
- ✅ Health endpoint ตอบกลับ: http://localhost:5000/api/health
- ✅ UI accessible ที่ http://localhost:5000 (HTTP 200)

#### Application Structure
- ✅ app.py — Flask Routes only (v0.12.0+ Modular Architecture)
- ✅ core/ — orchestrator.py, agent_factory.py, shared.py, utils.py
- ✅ agents/ — base_agent.py, hr_agent.py, accounting_agent.py, manager_agent.py, pm_agent.py, chat_agent.py
- ✅ prompts/ — System prompts as .md files (orchestrator, hr_agent, accounting_agent, manager_agent, pm_agent, chat_agent)
- ✅ index.html — Frontend v0.12.2 (chat bubbles, dark/light toggle, workspace picker, format modal, SSE streaming)
- ✅ test_cases.py — Automated test suite (6 use cases)
- ✅ quick-demo-check.py — Full validation (7 checks: 6 cases + health)
- ✅ backup/demo-inputs.txt — Demo scripts ready (ครบ 6 cases)
- ✅ backup/demo-script.md — Full demo walkthrough (3 cases)

#### Routing Test
- ✅ Tested: "สร้าง Invoice" → Correctly routed to **Accounting Agent**
- ✅ Agent badge displays properly in sidebar
- ✅ SSE streaming works
- ✅ Markdown rendering works (plain text ระหว่าง stream → HTML หลัง done)

### ❌ FAILED CHECKS

#### Backup Materials
- ❌ No screenshots in `backup/screenshots/` folder (ต้องการ 6 screenshots)
- ❌ No visual fallback if API fails during demo

#### Testing
- ⚠️ Automated test_cases.py not fully validated (timeout issues)
- ⚠️ All 6 use cases not tested end-to-end yet

---

## 30 MINUTES BEFORE DEMO — FINAL CHECKLIST

### Step 1: Environment Setup (5 min)
```bash
cd /home/zeroone/ai-poc-wsl

# Start server (WSL)
bash start.sh

# Verify health
curl http://localhost:5000/api/health
# Should return: {"status": "ok", "api_key_configured": true, "model": "..."}

# Test internet
curl -I https://openrouter.ai
# Should return HTTP 200
```

### Step 2: Browser Setup (2 min)
- [ ] เปิด http://localhost:5000 ใน browser
- [ ] ตรวจสอบว่า Model name แสดงใน sidebar footer ถูกต้อง
- [ ] เปิด backup/screenshots/ folder (เมื่อมี screenshots แล้ว)
- [ ] ปิด tabs อื่นที่มีข้อมูลส่วนตัว
- [ ] Zoom หน้าจอ 150-175% ให้ผู้บริหารเห็นชัด

### Step 3: System Settings (2 min)
- [ ] ปิด notifications (Slack, LINE, Email, Windows)
- [ ] ตั้ง "Do Not Disturb" mode
- [ ] ปิดโปรแกรมที่ไม่จำเป็น
- [ ] เช็คว่า desktop ไม่มีไฟล์ sensitive

### Step 4: Test All Use Cases (15 min)

**ต้องทดสอบทีละข้อ — MANDATORY:**

#### Case 1: HR — สัญญาจ้าง
```
Input: ร่างสัญญาจ้างพนักงานชื่อ สมชาย ใจดี ตำแหน่ง นักบัญชี เงินเดือน 35,000 บาท เริ่มงาน 1 มกราคม 2568
Expected:
- ✅ Orchestrator เลือก "hr"
- ✅ Agent badge แสดง HR Agent (สีเขียว)
- ✅ Output มีสัญญาจ้างภาษาไทย มีข้อมูล: ชื่อพนักงาน, ตำแหน่ง, เงินเดือน
- ✅ Output render เป็น Markdown หลัง done (ตาราง, หัวข้อ)
- ✅ มี disclaimer ที่ท้ายเอกสาร
```

#### Case 2: HR — Job Description
```
Input: สร้าง Job Description สำหรับตำแหน่ง HR Manager ในบริษัทขนาดกลาง
Expected:
- ✅ Orchestrator เลือก "hr"
- ✅ Output มี JD ครบ: Responsibilities, Requirements, Qualifications
```

#### Case 3: HR — อีเมลนโยบาย WFH
```
Input: ร่างอีเมลแจ้งพนักงานทุกคนเรื่องนโยบาย Work from Home ใหม่ สามารถทำงานจากบ้านได้สัปดาห์ละ 2 วัน
Expected:
- ✅ Orchestrator เลือก "hr"
- ✅ อีเมลเป็นทางการ มีหัวเรื่อง เนื้อหา
```

#### Case 4: Accounting — Invoice
```
Input: สร้าง Invoice สำหรับ บริษัท ABC จำกัด สำหรับค่าบริการที่ปรึกษา เดือนธันวาคม 2567 จำนวน 50,000 บาท
Expected:
- ✅ Orchestrator เลือก "accounting"
- ✅ Agent badge แสดง Accounting Agent (สีน้ำเงิน/ม่วง)
- ✅ มี Invoice format ถูกต้อง
- ✅ VAT 7% คำนวณถูก (3,500 บาท)
- ✅ ยอดรวม 53,500 บาท
- ✅ มี placeholder เลขภาษี
```

#### Case 5: Accounting — สรุปค่าใช้จ่าย
```
Input: สรุปรายการค่าใช้จ่ายของแผนก Marketing เดือนนี้ แบ่งเป็น ค่าโฆษณา 30,000 ค่าจ้างฟรีแลนซ์ 15,000 ค่าเดินทาง 5,000
Expected:
- ✅ Orchestrator เลือก "accounting"
- ✅ ตัวเลขรวมถูกต้อง (50,000 บาท)
- ✅ แยกหมวดหมู่ชัดเจน
- ✅ ไม่มี VAT (Expense Report ไม่มี VAT)
```

#### Case 6: Manager Advisor — Feedback พนักงาน
```
Input: ช่วยฉันวางแผนการพูดคุยกับพนักงานที่ส่งงานช้าและขาดงานบ่อย ฉันเป็น Team Lead และต้องการให้ Feedback อย่างสร้างสรรค์
Expected:
- ✅ Orchestrator เลือก "manager"
- ✅ Agent badge แสดง Manager Advisor (สีม่วง)
- ✅ มี script คำพูดจริงที่เอาไปพูดได้เลย
- ✅ มีแผนปฏิบัติได้ภายใน 48 ชั่วโมง
- ✅ มี disclaimer ท้ายเอกสาร
```

### Step 5: Prepare Backup Plan (3 min)
- [ ] รู้ว่าจะพูดอะไรถ้า internet ล่ม (ดู backup/demo-script.md)
- [ ] รู้ว่าจะพูดอะไรถ้า API ช้า
- [ ] เตรียมตัวตอบคำถามเรื่อง: cost, security, timeline

### Step 6: Final Run-Through (3 min)
- [ ] อ่าน demo script ใน backup/demo-script.md
- [ ] เปิด backup/demo-inputs.txt ไว้พร้อม copy-paste
- [ ] ฝึกพูด opening และ closing

---

## DEMO FLOW (7 นาที)

### Opening (30 วินาที)
> "วันนี้ผมจะ demo ระบบ AI Assistant ที่ผมสร้างขึ้นเพื่อช่วยพนักงานภายในบริษัท
> แนวคิดคือพนักงานพิมพ์งานเป็นภาษาธรรมดา แล้วระบบจะเลือก AI ที่เหมาะสมและทำงานให้อัตโนมัติ
> ขอ demo 3 กรณีครับ"

### Case 1: HR — สัญญาจ้าง (90 วินาที)
1. Copy input จาก demo-inputs.txt (Case 1)
2. Paste และ Enter
3. **ระหว่างรอ:** "ตรงนี้ sidebar แสดงว่าระบบเลือก HR Agent อัตโนมัติ ไม่ต้องเลือกเอง"
4. **เสร็จ:** "ได้สัญญาจ้างฉบับร่างภาษาไทยพร้อมใช้งานภายใน 30 วินาที ระบบ render เป็น markdown ให้อ่านง่ายด้วย"

### Case 2: Accounting — Invoice (60 วินาที)
1. Copy input (Case 4)
2. Paste และ Enter
3. **ระหว่างรอ:** "สังเกตว่า badge เปลี่ยนเป็น Accounting Agent อัตโนมัติ"
4. **เสร็จ:** "ได้ Invoice พร้อม VAT 7% คำนวณถูกต้อง"

### Case 3: Manager Advisor — Feedback (60 วินาที)
1. Copy input (Case 6)
2. Paste และ Enter
3. **ระหว่างรอ:** "นอกจาก HR กับบัญชี ระบบมี Manager Advisor สำหรับ Team Lead โดยเฉพาะ"
4. **เสร็จ:** "ได้ script คำพูดจริงที่เอาไปพูดได้เลย พร้อมแผนปฏิบัติภายใน 48 ชั่วโมง"

### Closing (60 วินาที)
> "สิ่งที่เห็นวันนี้คือ POC ที่ผมสร้างใน 2 คืน
> ถ้าได้รับการสนับสนุน ระบบจริงจะมี login, เชื่อมไฟล์, รองรับทุกแผนก
> ใช้เวลา 8 สัปดาห์
> ค่าใช้จ่าย $400-600/เดือน สำหรับ 30 คน (~14,000-21,000 บาท)
> มีคำถามไหมครับ?"

---

## BACKUP PLANS

### ถ้า Internet หลุด
> "ขอแสดง output ที่เตรียมไว้ก่อนครับ [เปิด screenshots]
> ระบบจริงจะทำแบบนี้แต่แบบ real-time"

### ถ้า API ช้า
> "Claude API ขึ้นกับ load ของระบบครับ production จะ optimize ตรงนี้"

### ถ้าหัวหน้าขอพิมพ์เอง
> "ได้เลยครับ" [เตรียมรับมือถ้า output ไม่สมบูรณ์]

---

## KNOWN ISSUES & WORKAROUNDS

### Issue 1: Model อาจตอบช้าในบางกรณี
**Workaround:** บอกหัวหน้าว่า "production จะ optimize timeout และ caching"

### Issue 2: Output อาจไม่สมบูรณ์ 100%
**Workaround:** ชี้ disclaimer และบอกว่า "ระบบมี human-in-the-loop เช็คก่อนใช้"

### Issue 3: Orchestrator อาจเลือก agent ผิดในบาง edge cases
**Workaround:** "prompt engineering จะ tune เพิ่มในระบบจริง"

### Issue 4: marked.js ต้องใช้ Internet
**Workaround:** ถ้า offline, output จะเป็น plain text แทน — ยังอ่านได้ปกติ

---

## Q&A PREPARATION

**ใช้เวลานานแค่ไหน?**
> "POC นี้ 2 คืน, Production 8 สัปดาห์"

**ราคาเท่าไหร่?**
> "$400-600/เดือน สำหรับ 30 คน หรือ ~14,000-21,000 บาท"

**ปลอดภัยไหม?**
> "OpenRouter/Anthropic ไม่เก็บข้อมูล API เพื่อ train model
> สามารถใช้ AWS Bedrock Singapore region ได้"

**รองรับภาษาอังกฤษไหม?**
> "ได้ครับ model รองรับ multilingual"

**Accuracy เท่าไหร่?**
> "เหมาะกับงานร่างเอกสาร ไม่เหมาะกับงาน critical decision
> ต้องมี human review ก่อนใช้งานจริง"

---

## 🎯 GO / NO-GO DECISION

### ⚠️ NO-GO — MUST FIX FIRST:
1. **สร้าง backup screenshots ทั้ง 6 cases**
   - ใช้เวลา ~40 นาที
   - Critical สำหรับ backup plan

2. **Test ทุก use case ให้ผ่าน 100%**
   - รัน: `PYTHONUTF8=1 python quick-demo-check.py`
   - ต้องแน่ใจว่า routing ถูกทั้ง 3 agents

### ✅ GO — IF:
1. มี screenshots ครบ 6 cases
2. Test ทุก case ผ่าน (6/6)
3. รู้ demo script และ Q&A
4. Internet stable
5. มีเวลา 30 นาที pre-check ก่อน demo

---

## NEXT STEPS

1. **รัน automated tests:**
   ```bash
   cd /home/zeroone/ai-poc-wsl
   source venv/bin/activate
   PYTHONUTF8=1 python quick-demo-check.py
   ```

2. **สร้าง screenshots:**
   - รัน server: `bash start.sh`
   - เปิด http://localhost:5000
   - Test ทุก case (6 cases) และ capture screenshot
   - Save ลง backup/screenshots/

3. **Final rehearsal:**
   - อ่าน demo script (backup/demo-script.md)
   - ฝึกพูดทั้งหมด
   - Time ตัวเองไม่เกิน 7 นาที

---

**Prepared by:** Claude Code
**Last Updated:** 2026-03-26 (v0.12.2)
**Contact:** [Your email/Slack]
