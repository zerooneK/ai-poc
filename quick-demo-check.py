#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Demo Check — Validates 5 core use cases
Run: PYTHONUTF8=1 python quick-demo-check.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"
TIMEOUT = 45

# 5 Demo Use Cases
CASES = [
    {
        "id": 1,
        "name": "HR — สัญญาจ้างพนักงาน",
        "input": "ร่างสัญญาจ้างพนักงานชื่อ สมชาย ใจดี ตำแหน่ง นักบัญชี เงินเดือน 35,000 บาท เริ่มงาน 1 มกราคม 2568",
        "expected_agent": "hr",
        "checks": ["สัญญา", "สมชาย", "35,000"]
    },
    {
        "id": 2,
        "name": "HR — Job Description",
        "input": "สร้าง Job Description สำหรับตำแหน่ง HR Manager ในบริษัทขนาดกลาง",
        "expected_agent": "hr",
        "checks": ["HR Manager", "Responsibility", "Qualification"]
    },
    {
        "id": 3,
        "name": "HR — อีเมลนโยบาย WFH",
        "input": "ร่างอีเมลแจ้งพนักงานทุกคนเรื่องนโยบาย Work from Home ใหม่ สามารถทำงานจากบ้านได้สัปดาห์ละ 2 วัน",
        "expected_agent": "hr",
        "checks": ["Work from Home", "2 วัน", "เรียน"]
    },
    {
        "id": 4,
        "name": "Accounting — Invoice",
        "input": "สร้าง Invoice สำหรับ บริษัท ABC จำกัด สำหรับค่าบริการที่ปรึกษา เดือนธันวาคม 2567 จำนวน 50,000 บาท",
        "expected_agent": "accounting",
        "checks": ["Invoice", "ABC", "50,000", "VAT"]
    },
    {
        "id": 5,
        "name": "Accounting — สรุปค่าใช้จ่าย",
        "input": "สรุปรายการค่าใช้จ่ายของแผนก Marketing เดือนนี้ แบ่งเป็น ค่าโฆษณา 30,000 ค่าจ้างฟรีแลนซ์ 15,000 ค่าเดินทาง 5,000",
        "expected_agent": "accounting",
        "checks": ["Marketing", "30,000", "15,000", "5,000"]
    },
    {
        "id": 6,
        "name": "Manager — Feedback พนักงาน",
        "input": "ช่วยฉันวางแผนการพูดคุยกับพนักงานที่ส่งงานช้าและขาดงานบ่อย ฉันเป็น Team Lead และต้องการให้ Feedback อย่างสร้างสรรค์",
        "expected_agent": "manager",
        "checks": ["Feedback", "48"]
    }
]

def check_health():
    """Check if server is running"""
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        return r.status_code == 200
    except:
        return False

def test_case(case):
    """Test a single use case"""
    print(f"\n{'─'*70}")
    print(f"TEST #{case['id']}: {case['name']}")
    print(f"{'─'*70}")
    print(f"Input: {case['input'][:60]}...")
    
    agent_detected = None
    output_text = ""
    errors = []
    
    try:
        r = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": case["input"]},
            stream=True,
            timeout=TIMEOUT
        )
        
        if r.status_code != 200:
            errors.append(f"HTTP {r.status_code}")
            return False, agent_detected, errors
        
        buffer = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            buffer += chunk
            while "\n\n" in buffer:
                line, buffer = buffer.split("\n\n", 1)
                if not line.startswith("data: "):
                    continue
                
                try:
                    data = json.loads(line[6:])
                except:
                    continue
                
                msg_type = data.get("type")
                
                if msg_type == "agent":
                    agent_detected = data.get("agent")
                    reason = data.get("reason", "")
                    print(f"→ Agent Selected: {agent_detected.upper()}")
                    print(f"→ Reason: {reason[:60]}...")
                    
                elif msg_type == "text":
                    output_text += data.get("content", "")
                    
                elif msg_type == "error":
                    errors.append(data.get("message", "Unknown error"))
                    
        # Validation
        print(f"→ Output Length: {len(output_text)} characters")
        
        # Check 1: Correct agent routing
        if agent_detected != case["expected_agent"]:
            errors.append(f"Wrong agent: expected '{case['expected_agent']}', got '{agent_detected}'")
        
        # Check 2: Required keywords in output
        missing_checks = []
        for check in case["checks"]:
            if check not in output_text:
                missing_checks.append(check)
        
        if missing_checks:
            errors.append(f"Missing keywords: {', '.join(missing_checks)}")
        
        # Check 3: Has disclaimer
        if "AI" not in output_text or "ร่าง" not in output_text:
            errors.append("Missing disclaimer")
        
        passed = len(errors) == 0 and len(output_text) > 200
        
        if passed:
            print("→ Status: ✅ PASS")
        else:
            print(f"→ Status: ❌ FAIL")
            for err in errors:
                print(f"  • {err}")
        
        return passed, agent_detected, errors
        
    except requests.Timeout:
        errors.append("Request timeout")
        print(f"→ Status: ❌ TIMEOUT")
        return False, agent_detected, errors
    except Exception as e:
        errors.append(str(e))
        print(f"→ Status: ❌ ERROR: {e}")
        return False, agent_detected, errors

def main():
    print("="*70)
    print("QUICK DEMO CHECK — AI Assistant POC")
    print("="*70)
    
    # Check server
    print("\n[1/7] Checking server health...")
    if not check_health():
        print("❌ Server not running at http://localhost:5000")
        print("   Start server: python app.py")
        sys.exit(1)
    print("✅ Server is running")
    
    # Run tests
    results = []
    for i, case in enumerate(CASES, 1):
        print(f"\n[{i+1}/7] Testing Case #{case['id']}...")
        passed, agent, errors = test_case(case)
        results.append({
            "case": case,
            "passed": passed,
            "agent": agent,
            "errors": errors
        })
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed_count = sum(1 for r in results if r["passed"])
    
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"{status} Case #{r['case']['id']}: {r['case']['name']}")
        if not r["passed"] and r["errors"]:
            for err in r["errors"]:
                print(f"      → {err}")
    
    print(f"\n{passed_count}/{len(CASES)} tests passed")
    
    if passed_count == len(CASES):
        print("\n🎯 GO FOR DEMO — All tests passed!")
    else:
        print(f"\n⚠️ NO-GO — Fix {len(CASES) - passed_count} failing tests before demo")
    
    print("="*70)
    
    sys.exit(0 if passed_count == len(CASES) else 1)

if __name__ == "__main__":
    main()
