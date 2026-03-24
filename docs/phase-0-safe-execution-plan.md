# Phase 0 Safe Execution Plan

เอกสารนี้เป็นแผนลงมือแบบลดความเสี่ยงสูงสุดสำหรับการปรับปรุง `Phase 0` โดยมีเป้าหมายคือเพิ่มความปลอดภัย แต่คงพฤติกรรมเดิมของระบบไว้ให้มากที่สุด และหลีกเลี่ยง regression ที่ทำให้เดโมหรือ flow หลักพัง

## Scope

ไฟล์หลักที่อยู่ในขอบเขต:
- `index.html`
- `app.py`

หัวข้อที่อยู่ในขอบเขต:
- ปิดความเสี่ยง XSS ฝั่ง frontend
- แก้ save flow ไม่ให้ false success
- จำกัด `workspace` path ให้ปลอดภัย
- ปิด `debug=True` สำหรับ runtime ปกติ

## Safety Rules

- แก้ทีละก้อนเล็ก ห้ามรวมหลายความเสี่ยงไว้ใน patch เดียว
- รักษา response shape, event flow, และ UX หลักเดิมไว้ก่อน
- ห้าม refactor ใหญ่ใน Phase 0
- หลังจบแต่ละก้อนต้องตรวจ smoke flow ทันที
- ถ้าก้อนใดทำให้ flow หลักเสีย ให้หยุดก่อนและ rollback ก้อนนั้น

## Baseline Before Any Change

ก่อนเริ่มแก้ ต้องตรวจว่า flow หลักเดิมยังใช้งานได้:
1. เปิดหน้าเว็บได้
2. ส่งข้อความและรับ response ได้
3. ข้อความแสดงผลใน chat ได้
4. save ได้
5. revise/discard ได้
6. เปลี่ยน workspace ได้ในพฤติกรรมปัจจุบัน

ถ้า baseline ยังไม่ผ่าน ห้ามเริ่ม Phase 0

## Execution Order

### Step 1: ปิด `debug=True` ใน `app.py`
เป้าหมาย:
- ลดความเสี่ยงด้าน deployment โดยแทบไม่กระทบ logic หลัก

สิ่งที่ต้องระวัง:
- อย่าเปลี่ยน behavior ของ route หรือ startup config อื่นพร้อมกัน

Smoke check หลังแก้:
- server start ได้
- หน้าเว็บเข้าได้
- `/api/health` ตอบกลับได้

Stop condition:
- server start ไม่ขึ้น
- health check ล้มเหลว

ความเสี่ยง:
- ต่ำมาก

### Step 2: harden `/api/workspace` ใน `app.py`
เป้าหมาย:
- จำกัด path ให้ปลอดภัย โดยยังคง flow เดิมให้มากที่สุด

แนวทางแบบ safe:
- รอบแรกใช้ allowlist หรือจำกัดไว้ใต้ project root ก่อน
- อย่าเปลี่ยน payload shape ของ API ถ้ายังไม่จำเป็น
- ถ้ามี path ที่ระบบใช้อยู่จริง ต้องรองรับ path นั้นก่อน

Smoke check หลังแก้:
- ตั้ง workspace เป็น path ที่ถูกต้องแล้วใช้งานได้
- path ที่ไม่ควรอนุญาตถูกปฏิเสธ
- file save ใน workspace ปกติยังทำงานได้

Stop condition:
- frontend เปลี่ยน workspace ไม่ได้แม้ path ถูกต้อง
- save flow ใช้งานไม่ได้หลังเปลี่ยน workspace

ความเสี่ยง:
- ปานกลาง

### Step 3: แก้ save flow ใน `app.py`
เป้าหมาย:
- ห้ามแสดงผลสำเร็จถ้าการเขียนไฟล์ล้มเหลว
- ต้องคง pending state เมื่อ save ไม่สำเร็จ

แนวทางแบบ safe:
- อย่าเปลี่ยนข้อความตอบกลับทั้งหมดพร้อมกัน
- เปลี่ยนเฉพาะ logic แยก `success/error`
- รักษา flow เดิมของ `save`, `revise`, `discard` ให้เหมือนเดิมมากที่สุด
- ถ้าจำเป็นให้เพิ่ม error branch โดยไม่เปลี่ยน happy path มาก

Smoke check หลังแก้:
- save สำเร็จแล้วย้ายไฟล์ถูกต้อง
- save ล้มเหลวแล้วแจ้ง error ชัดเจน
- save ล้มเหลวแล้ว pending state ยังอยู่
- revise หลัง save fail ยังทำงานได้
- discard ยังล้าง state ได้ถูกต้อง

Stop condition:
- save ทุกเคส fail
- save สำเร็จแต่ไฟล์ไม่ถูกสร้าง
- revise/discard ใช้งานต่อไม่ได้

ความเสี่ยง:
- ปานกลางถึงสูง

### Step 4: ปิด XSS แบบค่อยเป็นค่อยไปใน `index.html`
เป้าหมาย:
- ลดการใช้ `innerHTML` กับข้อมูลจาก LLM/server โดยไม่ทำให้ UI พัง

แนวทางแบบ safe:
- แก้ทีละจุด ไม่ rewrite ระบบ render ทั้งหน้า
- เริ่มจากจุดที่รับข้อความจาก LLM ก่อน
- ถ้าต้องรองรับ markdown ให้ใช้ sanitizer หลัง parse
- จุดที่เป็น plain text ให้ใช้ `textContent` ก่อนเสมอ
- อย่าเปลี่ยน structure DOM ที่ event handlers พึ่งพาอยู่โดยไม่จำเป็น

Smoke check หลังแก้:
- ข้อความ chat แสดงผลได้
- line breaks ยังพอใช้งานได้
- markdown ที่จำเป็นยังแสดงผลได้
- PM plan / file panel / status message ยังไม่พัง
- browser console ไม่มี JavaScript error ใหม่

Stop condition:
- chat render ไม่ขึ้น
- UI หลักหยุดทำงาน
- event handler หลุดเพราะ DOM structure เปลี่ยน

ความเสี่ยง:
- สูงสุดใน Phase 0

## Recommended Patch Strategy

ให้แยกการแก้เป็น 4 patch หรือ 4 PR:
1. `app.py`: disable debug mode only
2. `app.py`: workspace validation only
3. `app.py`: save flow hardening only
4. `index.html`: XSS mitigation only

ห้ามรวม `index.html` และ `app.py` ใน patch เดียวถ้ายังไม่จำเป็น

## Rollback Rules

- ถ้า patch ใดทำให้ flow หลักข้อใดข้อหนึ่งจาก baseline พัง ให้ rollback patch นั้นทันที
- ถ้า patch ผ่านเฉพาะบางกรณี แต่กระทบ demo flow หลัก ให้หยุดและแก้ patch นั้นก่อนเริ่ม patch ถัดไป
- ห้ามเดินหน้าต่อถ้า save, chat render, หรือ workspace flow เสีย

## Minimum Smoke Test Checklist After Every Patch

- [ ] เปิดหน้าเว็บได้
- [ ] ส่งข้อความได้
- [ ] response แสดงผลในหน้าได้
- [ ] ไม่มี JavaScript error ใหม่ที่ทำให้ flow หลักหยุด
- [ ] save/revise/discard ยังทำงานตามกรณีที่เกี่ยวข้อง
- [ ] workspace flow ยังทำงานตามกรณีที่เกี่ยวข้อง

คำสั่งแนะนำสำหรับรอบยืนยัน Phase 0:
```bash
.\venv\Scripts\python.exe smoke_test_phase0.py
```

## Windows Thai Input Note

สำหรับ ad-hoc smoke test ที่ส่งคำ confirmation ภาษาไทย เช่น `บันทึก` และ `ยกเลิก` ผ่าน Windows shell:
- ให้ใช้ `.\\venv\\Scripts\\python.exe`
- ตั้ง `PYTHONUTF8=1` ก่อนรันถ้าเป็น command line test
- ส่ง payload เป็น UTF-8 JSON เสมอ
- ถ้าทดสอบผ่าน inline shell script หรือ heredoc ให้ใช้ Unicode escape สำหรับคำภาษาไทยเพื่อป้องกันการถูกแปลงเป็น `??????`

หมายเหตุ:
- false alarm ที่เคยเกิดใน smoke test confirmation flow ภาษาไทยมาจาก shell encoding ไม่ใช่ regression ใน backend
- ก่อนสรุปว่า backend พัง ต้องยืนยันซ้ำด้วย UTF-8/Unicode-safe payload ก่อนเสมอ

## Success Criteria

จะถือว่า Phase 0 สำเร็จแบบปลอดภัยเมื่อ:
- ระบบยังใช้งาน flow หลักได้เหมือนเดิม
- ไม่มี false success ใน save flow
- path สำหรับ workspace ถูกจำกัดอย่างปลอดภัย
- frontend ลดความเสี่ยง XSS ลงอย่างชัดเจน
- ไม่มี regression ร้ายแรงใน chat, save, revise, discard, และ workspace flow

## Confidence Assessment

ถ้าทำตามแผนนี้แบบทีละก้อนและตรวจหลังทุกก้อน:
- โอกาสสำเร็จโดยไม่เกิด regression ร้ายแรง: ค่อนข้างสูง
- งานความเสี่ยงต่ำสุด: ปิด `debug=True`
- งานความเสี่ยงสูงสุด: ปรับ safe rendering ใน `index.html`

ข้อสำคัญ:
- แผนนี้ลดความเสี่ยงได้มาก แต่ไม่ใช่การรับประกัน 100%
- จุดที่ต้องระวังที่สุดคือการทำให้ UI render เปลี่ยนพฤติกรรม และการทำให้ save flow เปลี่ยน contract โดยไม่ตั้งใจ
