import requests
import json
import os

BASE_URL = "http://localhost:5000"
SEP = "\u2500" * 60

# (label, message, expected_agent, min_chars, check_keywords)
CASES = [
    ("HR #1 \u2014 \u0e2a\u0e31\u0e0d\u0e0d\u0e32\u0e08\u0e49\u0e32\u0e07",
     "\u0e23\u0e48\u0e32\u0e07\u0e2a\u0e31\u0e0d\u0e0d\u0e32\u0e08\u0e49\u0e32\u0e07\u0e1e\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19\u0e0a\u0e37\u0e48\u0e2d "
     "\u0e2a\u0e21\u0e0a\u0e32\u0e22 \u0e43\u0e08\u0e14\u0e35 "
     "\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07 \u0e19\u0e31\u0e01\u0e1a\u0e31\u0e0d\u0e0a\u0e35 "
     "\u0e40\u0e07\u0e34\u0e19\u0e40\u0e14\u0e37\u0e2d\u0e19 35,000 \u0e1a\u0e32\u0e17 "
     "\u0e40\u0e23\u0e34\u0e48\u0e21\u0e07\u0e32\u0e19 1 \u0e21\u0e01\u0e23\u0e32\u0e04\u0e21 2568",
     "hr", 400, ["\u0e2a\u0e21\u0e0a\u0e32\u0e22", "35,000"]),

    ("HR #2 \u2014 Job Description",
     "\u0e2a\u0e23\u0e49\u0e32\u0e07 Job Description "
     "\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07 HR Manager "
     "\u0e43\u0e19\u0e1a\u0e23\u0e34\u0e29\u0e31\u0e17\u0e02\u0e19\u0e32\u0e14\u0e01\u0e25\u0e32\u0e07",
     "hr", 300, ["HR Manager"]),

    ("HR #3 \u2014 \u0e2d\u0e35\u0e40\u0e21\u0e25\u0e19\u0e42\u0e22\u0e1a\u0e32\u0e22 WFH",
     "\u0e23\u0e48\u0e32\u0e07\u0e2d\u0e35\u0e40\u0e21\u0e25\u0e41\u0e08\u0e49\u0e07\u0e1e\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19\u0e17\u0e38\u0e01\u0e04\u0e19"
     "\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e19\u0e42\u0e22\u0e1a\u0e32\u0e22 Work from Home "
     "\u0e43\u0e2b\u0e21\u0e48 \u0e2a\u0e32\u0e21\u0e32\u0e23\u0e16\u0e17\u0e33\u0e07\u0e32\u0e19\u0e08\u0e32\u0e01"
     "\u0e1a\u0e49\u0e32\u0e19\u0e44\u0e14\u0e49\u0e2a\u0e31\u0e1b\u0e14\u0e32\u0e2b\u0e4c\u0e25\u0e30 2 \u0e27\u0e31\u0e19",
     "hr", 200, ["Work from Home"]),

    ("Accounting #4 \u2014 Invoice",
     "\u0e2a\u0e23\u0e49\u0e32\u0e07 Invoice \u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a "
     "\u0e1a\u0e23\u0e34\u0e29\u0e31\u0e17 ABC \u0e08\u0e33\u0e01\u0e31\u0e14 "
     "\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e04\u0e48\u0e32\u0e1a\u0e23\u0e34\u0e01\u0e32\u0e23"
     "\u0e17\u0e35\u0e48\u0e1b\u0e23\u0e36\u0e01\u0e29\u0e32 \u0e40\u0e14\u0e37\u0e2d\u0e19"
     "\u0e18\u0e31\u0e19\u0e27\u0e32\u0e04\u0e21 2567 \u0e08\u0e33\u0e19\u0e27\u0e19 50,000 \u0e1a\u0e32\u0e17",
     "accounting", 300, ["50,000", "ABC"]),

    ("Accounting #5 \u2014 \u0e2a\u0e23\u0e38\u0e1b\u0e04\u0e48\u0e32\u0e43\u0e0a\u0e49\u0e08\u0e48\u0e32\u0e22",
     "\u0e2a\u0e23\u0e38\u0e1b\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23\u0e04\u0e48\u0e32\u0e43\u0e0a\u0e49\u0e08\u0e48\u0e32\u0e22"
     "\u0e02\u0e2d\u0e07\u0e41\u0e1c\u0e19\u0e01 Marketing \u0e40\u0e14\u0e37\u0e2d\u0e19\u0e19\u0e35\u0e49 "
     "\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e1b\u0e47\u0e19 \u0e04\u0e48\u0e32\u0e42\u0e06\u0e29\u0e13\u0e32 30,000 "
     "\u0e04\u0e48\u0e32\u0e08\u0e49\u0e32\u0e07\u0e1f\u0e23\u0e35\u0e41\u0e25\u0e19\u0e0b\u0e4c 15,000 "
     "\u0e04\u0e48\u0e32\u0e40\u0e14\u0e34\u0e19\u0e17\u0e32\u0e07 5,000",
     "accounting", 200, ["30,000", "Marketing"]),

    ("Manager #6 \u2014 Feedback \u0e1e\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19",
     "\u0e0a\u0e48\u0e27\u0e22\u0e09\u0e31\u0e19\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19\u0e01\u0e32\u0e23"
     "\u0e1e\u0e39\u0e14\u0e04\u0e38\u0e22\u0e01\u0e31\u0e1a\u0e1e\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19"
     "\u0e17\u0e35\u0e48\u0e2a\u0e48\u0e07\u0e07\u0e32\u0e19\u0e0a\u0e49\u0e32\u0e41\u0e25\u0e30"
     "\u0e02\u0e32\u0e14\u0e07\u0e32\u0e19\u0e1a\u0e48\u0e2d\u0e22 "
     "\u0e09\u0e31\u0e19\u0e40\u0e1b\u0e47\u0e19 Team Lead "
     "\u0e41\u0e25\u0e30\u0e15\u0e49\u0e2d\u0e07\u0e01\u0e32\u0e23\u0e43\u0e2b\u0e49 Feedback "
     "\u0e2d\u0e22\u0e48\u0e32\u0e07\u0e2a\u0e23\u0e49\u0e32\u0e07\u0e2a\u0e23\u0e23\u0e04\u0e4c",
     "manager", 300, []),
]

# PM Agent test cases: (label, message, expected_file_count)
PM_CASES = [
    ("PM #7 \u2014 HR + Accounting (\u0e2a\u0e31\u0e0d\u0e0d\u0e32\u0e08\u0e49\u0e32\u0e07 + Invoice)",
     "\u0e2a\u0e23\u0e49\u0e32\u0e07\u0e2a\u0e31\u0e0d\u0e0d\u0e32\u0e08\u0e49\u0e32\u0e07\u0e41\u0e25\u0e30 Invoice "
     "\u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e1e\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19\u0e0a\u0e37\u0e48\u0e2d "
     "\u0e27\u0e34\u0e20\u0e32 \u0e23\u0e31\u0e01\u0e44\u0e17\u0e22 "
     "\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07 \u0e19\u0e31\u0e01\u0e1e\u0e31\u0e12\u0e19\u0e32\u0e0b\u0e2d\u0e1f\u0e15\u0e4c\u0e41\u0e27\u0e23\u0e4c "
     "\u0e40\u0e07\u0e34\u0e19\u0e40\u0e14\u0e37\u0e2d\u0e19 45,000 \u0e1a\u0e32\u0e17",
     2),

    ("PM #8 \u2014 HR + Manager (JD + \u0e41\u0e1c\u0e19 Onboarding)",
     "\u0e2a\u0e23\u0e49\u0e32\u0e07 Job Description \u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07 "
     "Data Analyst "
     "\u0e41\u0e25\u0e30\u0e27\u0e32\u0e07\u0e41\u0e1c\u0e19\u0e01\u0e32\u0e23 Onboarding "
     "\u0e1e\u0e19\u0e31\u0e01\u0e07\u0e32\u0e19\u0e43\u0e2b\u0e21\u0e48\u0e43\u0e19\u0e15\u0e33\u0e41\u0e2b\u0e19\u0e48\u0e07\u0e19\u0e35\u0e49",
     2),
]


def test_case(label, message, expected_agent=None, min_chars=100, check_keywords=None):
    print(f"\n{SEP}")
    print(f"TEST: {label}")
    print(f"INPUT: {message[:70]}...")
    print(SEP)

    agent_selected = None
    output_text = ""
    status = "\u274c FAIL"
    fail_reason = ""

    with requests.post(f"{BASE_URL}/api/chat",
                       json={"message": message, "session_id": "test-session"},
                       stream=True, timeout=90) as r:
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
                    print(f"  \u2192 Agent: {agent_selected.upper()} ({data.get('reason', '')[:60]})")
                elif t == "text":
                    output_text += data.get("content", "")
                elif t == "done":
                    status = "\u2705 PASS"
                elif t == "error":
                    print(f"  ERROR: {data.get('message')}")
                    fail_reason = "server error"

    if expected_agent and agent_selected != expected_agent:
        status = "\u274c FAIL"
        fail_reason = f"wrong routing: expected {expected_agent}, got {agent_selected}"

    if len(output_text) < min_chars:
        status = "\u274c FAIL"
        fail_reason = f"output too short: {len(output_text)} chars (min {min_chars})"

    if check_keywords and not fail_reason:
        for kw in check_keywords:
            if kw not in output_text:
                status = "\u274c FAIL"
                fail_reason = f"missing keyword in output: '{kw}'"
                break

    print(f"  Output: {len(output_text)} chars")
    if fail_reason:
        print(f"  Reason: {fail_reason}")
    print(f"  Status: {status}")
    return status == "\u2705 PASS"


def test_pm_case(label, message, expected_file_count=None):
    """Test PM Agent two-step flow: generate subtasks -> confirm save."""
    print(f"\n{SEP}")
    print(f"TEST: {label}")
    print(f"INPUT: {message[:70]}...")
    print(SEP)

    pending_temp_paths = []
    status = "\u274c FAIL"
    fail_reason = ""

    # ── Step 1: Send PM task ──────────────────────────────────────────
    with requests.post(f"{BASE_URL}/api/chat",
                       json={"message": message, "session_id": "test-pm-session"},
                       stream=True, timeout=180) as r:
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
                if t == "pm_plan":
                    subtasks = data.get("subtasks", [])
                    print(f"  \u2192 PM Plan: {len(subtasks)} subtasks")
                    for s in subtasks:
                        print(f"      [{s.get('agent')}] {s.get('task', '')[:55]}")
                elif t == "pending_file":
                    path = data.get("temp_path", "")
                    pending_temp_paths.append(path)
                    print(f"  \u2192 Staged: {os.path.basename(path)}")
                elif t == "agent":
                    print(f"  \u2192 Agent: {data.get('agent', '').upper()} (subtask)")
                elif t == "error":
                    fail_reason = f"step 1 error: {data.get('message')}"

    if fail_reason:
        print(f"  Reason: {fail_reason}")
        print(f"  Status: {status}")
        return False

    if not pending_temp_paths:
        print(f"  Reason: no staged files received")
        print(f"  Status: {status}")
        return False

    print(f"  Staged: {len(pending_temp_paths)} file(s)")

    if expected_file_count and len(pending_temp_paths) != expected_file_count:
        print(f"  WARN: expected {expected_file_count} files, got {len(pending_temp_paths)}")

    # ── Step 2: Confirm save ──────────────────────────────────────────
    print(f"  \u2192 Confirming save...")
    save_msg = "\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01"  # บันทึก

    with requests.post(f"{BASE_URL}/api/chat",
                       json={
                           "message": save_msg,
                           "session_id": "test-pm-session",
                           "pending_temp_paths": pending_temp_paths,
                       },
                       stream=True, timeout=60) as r:
        if r.status_code != 200:
            print(f"  HTTP Error on save: {r.status_code}")
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
                if t == "text":
                    content = data.get("content", "").strip()
                    if content:
                        print(f"  \u2192 Saved: {content[:60]}")
                elif t == "done":
                    status = "\u2705 PASS"
                elif t == "save_failed":
                    fail_reason = f"save failed: {data.get('message')}"
                    status = "\u274c FAIL"
                elif t == "error":
                    fail_reason = f"save error: {data.get('message')}"
                    status = "\u274c FAIL"

    if fail_reason:
        print(f"  Reason: {fail_reason}")
    print(f"  Status: {status}")
    return status == "\u2705 PASS"


# ── Run all tests ──────────────────────────────────────────────────────────────

results = []

print(f"\n{'='*60}")
print("SINGLE-AGENT TESTS (Cases 1-6)")
print('='*60)
for label, msg, expected_agent, min_chars, keywords in CASES:
    ok = test_case(label, msg, expected_agent, min_chars, keywords)
    results.append((label, ok))

print(f"\n{'='*60}")
print("PM AGENT TESTS (Cases 7-8)")
print('='*60)
for label, msg, expected_files in PM_CASES:
    ok = test_pm_case(label, msg, expected_files)
    results.append((label, ok))

print(f"\n{'='*60}")
print("SUMMARY")
print('='*60)
for label, ok in results:
    print(f"  {'\u2705' if ok else '\u274c'}  {label}")
passed = sum(1 for _, ok in results if ok)
print(f"\n  {passed}/{len(results)} passed")
if passed == len(results):
    print("  \U0001f7e2 ALL PASS — ready for demo")
else:
    print(f"  \U0001f534 {len(results) - passed} FAILED — check issues above")
