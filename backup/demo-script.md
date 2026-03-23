# Demo Script — Internal AI Assistant POC

## Pre-Demo Checklist (30 นาทีก่อน)

### Environment
- [ ] Flask server รันอยู่ที่ http://localhost:5000
- [ ] เปิด browser tab ที่ http://localhost:5000 ไว้แล้ว
- [ ] Internet connection stable (test: curl https://openrouter.ai)
- [ ] ปิด notification ทั้งหมด (Slack, LINE, Email, System)
- [ ] Zoom หน้าจอให้เห็นชัด (150-175%)
- [ ] เปิด backup/screenshots/ ไว้ใน tab สำรอง

### Materials
- [ ] backup/demo-inputs.txt พร้อม copy-paste
- [ ] Screenshots ของ output ที่ดีที่สุดอยู่ใน backup/screenshots/
- [ ] รู้ว่าถ้า internet หลุดจะทำอะไร

---

## Demo Flow (5 นาที)

### Opening (30 วินาที)
> "วันนี้ผมจะ demo ระบบ AI Assistant ที่ผมสร้างขึ้นเพื่อช่วยพนักงานภายในบริษัท
> 
> แนวคิดคือพนักงานพิมพ์งานเป็นภาษาธรรมดา แล้วระบบจะเลือก AI ที่เหมาะสมและทำงานให้อัตโนมัติ
> 
> ขอ demo 2 กรณีครับ"

### Demo Case 1 — HR (90 วินาที)

**Action:**
1. Copy Case 1 จาก backup/demo-inputs.txt
2. Paste ลงในช่อง input
3. กด Enter

**Script:**
> [ระหว่างรอ] "ตรงนี้ sidebar แสดงว่าระบบเลือก HR Agent โดยอัตโนมัติ ไม่ต้องเลือกเอง"
> 
> [เสร็จ] "ได้สัญญาจ้างฉบับร่างภาษาไทยพร้อมใช้งานภายใน 30 วินาที"

### Demo Case 2 — Accounting (60 วินาที)

**Action:**
1. Copy Case 4 จาก backup/demo-inputs.txt (Invoice)
2. Paste และ Enter

**Script:**
> "สังเกตว่า badge เปลี่ยนเป็น Accounting Agent อัตโนมัติ 
> ระบบรู้เองว่างานไหนเป็นงานบัญชี"

### Closing (60 วินาที)
> "สิ่งที่เห็นวันนี้คือ POC ที่ผมสร้างใน 2 คืน
> 
> ถ้าได้รับการสนับสนุน ระบบจริงจะมี:
> - Login และ user management
> - เชื่อมไฟล์บนเครื่องหรือ SharePoint
> - รองรับทุกแผนก (Marketing, Sales, Legal)
> - ใช้เวลาประมาณ 8 สัปดาห์
> 
> ค่าใช้จ่าย: ประมาณ $400-600/เดือน สำหรับ 30 คน (~14,000-21,000 บาท)
> 
> มีคำถามไหมครับ?"

---

## Backup Plans

### ถ้า Internet หลุด
> "ขอแสดง output ที่เตรียมไว้ก่อนครับ [เปิด screenshots]
> 
> ระบบจริงจะทำแบบนี้แต่แบบ real-time ครับ"

### ถ้า API ช้ากว่าปกติ
> "Claude API ขึ้นกับ load ของระบบครับ production จะ optimize ตรงนี้"

### ถ้าหัวหน้าขอพิมพ์เอง
> "ได้เลยครับ"
> 
> [เตรียมรับมือถ้า output ไม่สมบูรณ์]
> "prompt จริงจะ tune มากกว่านี้ครับ"

### ถ้าถามเรื่องค่าใช้จ่าย
> "ประมาณ $400-600 ต่อเดือนสำหรับ 30 คน หรือ ~14,000-21,000 บาท
> 
> ตัวเลขจริงรู้ได้หลังใช้งาน 1 เดือนแรกครับ"

### ถ้าถามเรื่อง Data Privacy
> "OpenRouter/Anthropic ระบุชัดว่าไม่ใช้ข้อมูล API เพื่อ train model ครับ
> 
> ถ้า IT ต้องการความมั่นใจเพิ่ม เราสามารถเปลี่ยนเป็น AWS Bedrock
> ที่ข้อมูลอยู่ใน Singapore region ได้ครับ ราคาเท่ากัน"

### ถ้าถามเรื่อง Accuracy
> "ระบบมี disclaimer ที่ท้ายเอกสารทุกฉบับครับ
> 
> แนะนำให้มี human-in-the-loop เช็คก่อนใช้งานจริง
> เหมาะกับงานที่ใช้เวลานาน เช่น ร่างเอกสาร ไม่เหมาะกับงาน critical
> เช่น การตัดสินใจทางการเงินสูง"

---

## Q&A Prep

**ใช้เวลานานแค่ไหน?**
> "POC นี้ 2 คืน, Production 8 สัปดาห์"

**ราคาเท่าไหร่?**
> "$400-600/เดือน สำหรับ 30 คน"

**ปลอดภัยไหม?**
> "Provider ไม่เก็บข้อมูล, สามารถใช้ private cloud ได้"

**รองรับภาษาอังกฤษไหม?**
> "ได้ครับ model รองรับ multilingual"

**Scale ได้เท่าไหร่?**
> "รองรับได้หลักร้อยคน แต่ต้อง tune infrastructure"

