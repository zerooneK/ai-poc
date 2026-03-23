# PRE-DEMO CHECKLIST — Internal AI Assistant POC
**Demo Date:** 2026-03-23 (หรือตามกำหนด)  
**Duration:** 5 นาที  
**Status:** 🟡 NEEDS ATTENTION (อ่านด้านล่าง)

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

# Save เป็น:
# - case1-hr-contract.png
# - case2-hr-jd.png
# - case3-hr-email.png
# - case4-accounting-invoice.png
# - case5-accounting-expense.png
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
- ✅ Flask server สามารถรันได้ (`python app.py`)
- ✅ Dependencies ครบ (flask, flask-cors, openai, python-dotenv)
- ✅ .env file มี API key configured
- ✅ Health endpoint ตอบกลับ: http://localhost:5000/api/health
- ✅ UI accessible ที่ http://localhost:5000 (HTTP 200)

#### Application Structure
- ✅ app.py — Backend with Orchestrator + HR/Accounting agents
- ✅ index.html — Frontend with SSE streaming
- ✅ test_cases.py — Automated test suite
- ✅ backup/demo-inputs.txt — Demo scripts ready
- ✅ backup/demo-script.md — Full demo walkthrough

#### Routing Test
- ✅ Tested: "สร้าง Invoice" → Correctly routed to **Accounting Agent**
- ✅ Agent badge displays properly in sidebar
- ✅ SSE streaming works

### ❌ FAILED CHECKS

#### Backup Materials
- ❌ No screenshots in `backup/screenshots/` folder
- ❌ No visual fallback if API fails during demo

#### Testing
- ⚠️ Automated test_cases.py not fully validated (timeout issues)
- ⚠️ All 5 use cases not tested end-to-end yet

---

## 30 MINUTES BEFORE DEMO — FINAL CHECKLIST

### Step 1: Environment Setup (5 min)
```bash
cd D:/ai-poc

# Start server
python app.py

# Verify health
curl http://localhost:5000/api/health
# Should return: {"status": "ok", "api_key_configured": true}

# Test internet
curl -I https://openrouter.ai
# Should return HTTP 200
```

### Step 2: Browser Setup (2 min)
- [ ] เปิด http://localhost:5000 ใน browser
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
- ✅ Output มีสัญญาจ้างภาษาไทย
- ✅ มีข้อมูล: ชื่อพนักงาน, ตำแหน่ง, เงินเดือน
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

## DEMO FLOW (5 นาที)

### Opening (30 วินาที)
> "วันนี้ผมจะ demo ระบบ AI Assistant ที่ผมสร้างขึ้นเพื่อช่วยพนักงานภายในบริษัท  
> แนวคิดคือพนักงานพิมพ์งานเป็นภาษาธรรมดา แล้วระบบจะเลือก AI ที่เหมาะสมและทำงานให้อัตโนมัติ  
> ขอ demo 2 กรณีครับ"

### Case 1: HR — สัญญาจ้าง (90 วินาที)
1. Copy input จาก demo-inputs.txt
2. Paste และ Enter
3. **ระหว่างรอ:** "ตรงนี้ sidebar แสดงว่าระบบเลือก HR Agent อัตโนมัติ"
4. **เสร็จ:** "ได้สัญญาจ้างฉบับร่างภาษาไทยพร้อมใช้งานภายใน 30 วินาที"

### Case 2: Accounting — Invoice (60 วินาที)
1. Copy input (Case 4)
2. Paste และ Enter
3. **ระหว่างรอ:** "สังเกตว่า badge เปลี่ยนเป็น Accounting Agent อัตโนมัติ"

### Closing (60 วินาที)
> "สิ่งที่เห็นวันนี้คือ POC ที่ผมสร้างใน 2 คืน  
> ถ้าได้รับการสนับสนุน ระบบจริงจะมี login, เชื่อมไฟล์, รองรับทุกแผนก  
> ใช้เวลา 8 สัปดาห์  
> ค่าใช้จ่าย $400-600/เดือน สำหรับ 30 คน  
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
1. **สร้าง backup screenshots ทั้ง 5 cases**  
   - ใช้เวลา ~30 นาที
   - Critical สำหรับ backup plan

2. **Test ทุก use case ให้ผ่าน 100%**  
   - ต้องแน่ใจว่า routing ถูก
   - Output มีคุณภาพ

### ✅ GO — IF:
1. มี screenshots ครบ 5 cases
2. Test ทุก case ผ่าน
3. รู้ demo script และ Q&A
4. Internet stable
5. มีเวลา 30 นาที pre-check ก่อน demo

---

## NEXT STEPS

1. **รัน automated tests:**
   ```bash
   cd D:/ai-poc
   PYTHONUTF8=1 python test_cases.py
   ```

2. **สร้าง screenshots:**
   - รัน server: `python app.py`
   - เปิด http://localhost:5000
   - Test ทุก case และ capture screenshot
   - Save ลง backup/screenshots/

3. **Final rehearsal:**
   - อ่าน demo script
   - ฝึกพูดทั้งหมด
   - Time ตัวเองไม่เกิน 5 นาที

---

**Prepared by:** Claude Code  
**Last Updated:** 2026-03-23  
**Contact:** [Your email/Slack]
