import requests
import json

BASE_URL = "http://localhost:5000"

CASES = [
    ("HR #1 — สัญญาจ้าง",
     "ร่างสัญญาจ้างพนักงานชื่อ สมชาย ใจดี ตำแหน่ง นักบัญชี เงินเดือน 35,000 บาท เริ่มงาน 1 มกราคม 2568"),
    ("HR #2 — Job Description",
     "สร้าง Job Description สำหรับตำแหน่ง HR Manager ในบริษัทขนาดกลาง"),
    ("HR #3 — อีเมลนโยบาย WFH",
     "ร่างอีเมลแจ้งพนักงานทุกคนเรื่องนโยบาย Work from Home ใหม่ สามารถทำงานจากบ้านได้สัปดาห์ละ 2 วัน"),
    ("Accounting #4 — Invoice",
     "สร้าง Invoice สำหรับ บริษัท ABC จำกัด สำหรับค่าบริการที่ปรึกษา เดือนธันวาคม 2567 จำนวน 50,000 บาท"),
    ("Accounting #5 — สรุปค่าใช้จ่าย",
     "สรุปรายการค่าใช้จ่ายของแผนก Marketing เดือนนี้ แบ่งเป็น ค่าโฆษณา 30,000 ค่าจ้างฟรีแลนซ์ 15,000 ค่าเดินทาง 5,000"),
]

SEP = "─" * 60

def test_case(label, message):
    print(f"\n{SEP}")
    print(f"TEST: {label}")
    print(f"INPUT: {message[:60]}...")
    print(SEP)

    agent_selected = None
    output_chars = 0
    has_disclaimer = False
    status = "❌ FAIL"

    with requests.post(f"{BASE_URL}/api/chat",
                       json={"message": message},
                       stream=True, timeout=60) as r:
        if r.status_code != 200:
            print(f"  HTTP Error: {r.status_code}")
            return False

        buffer = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            buffer += chunk
            while "\n\n" in buffer:
                line, buffer = buffer.split("\n\n", 1)
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                t = data.get("type")
                if t == "agent":
                    agent_selected = data.get("agent")
                    print(f"  → Agent: {agent_selected.upper()} ({data.get('reason', '')})")
                elif t == "text":
                    output_chars += len(data.get("content", ""))
                    if "AI" in data.get("content", "") and "ร่าง" in data.get("content", ""):
                        has_disclaimer = True
                elif t == "done":
                    status = "✅ PASS"
                elif t == "error":
                    print(f"  ERROR: {data.get('message')}")
                    status = "❌ FAIL"

    print(f"  Output: {output_chars} chars")
    print(f"  Status: {status}")
    return status == "✅ PASS"

results = []
for label, msg in CASES:
    ok = test_case(label, msg)
    results.append((label, ok))

print(f"\n{'═'*60}")
print("SUMMARY")
print('═'*60)
for label, ok in results:
    print(f"  {'✅' if ok else '❌'}  {label}")
passed = sum(1 for _, ok in results if ok)
print(f"\n  {passed}/{len(CASES)} passed")
