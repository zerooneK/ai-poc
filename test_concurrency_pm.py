"""
D2 Concurrency Test — AI Assistant POC
=======================================
ทดสอบ 4 test cases:
  TC-1: 2 PM requests พร้อมกัน
  TC-2: PM request + workspace switch กลางคัน
  TC-3: 3 PM requests พร้อมกัน (rate limit simulation)
  TC-4: memory leak baseline (10 sequential requests)

วิธีรัน:
  python3 test_concurrency_pm.py
  python3 test_concurrency_pm.py --host http://192.168.1.10:5000
  python3 test_concurrency_pm.py --tc 1        # รันแค่ TC-1
  python3 test_concurrency_pm.py --tc 1 2 3 4  # รันทุก TC
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error

# ─── Config ───────────────────────────────────────────────────────────────────

DEFAULT_HOST = os.getenv("TEST_HOST", "http://localhost:5000")
TIMEOUT_PER_REQUEST = 180   # seconds — PM task อาจนาน 60-120s
WORKSPACE_A = "./workspace"
WORKSPACE_B = "/tmp/ai-poc-test-workspace-b"

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
INFO = "\033[94mℹ️ \033[0m"
WARN = "\033[93m⚠️ \033[0m"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def sse_collect(host, message, result_dict, key, timeout=TIMEOUT_PER_REQUEST):
    """Send a chat message and collect all SSE events. Stores result in result_dict[key]."""
    url = f"{host}/api/chat"
    payload = json.dumps({
        "message": message,
        "session_id": f"test-{key}-{int(time.time())}",
        "output_format": "md",
        "conversation_history": []
    }).encode("utf-8")

    events = []
    error = None
    start = time.time()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            buffer = b""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n\n" in buffer:
                    line, buffer = buffer.split(b"\n\n", 1)
                    line = line.decode("utf-8", errors="replace").strip()
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            events.append(data)
                            if data.get("type") == "done":
                                break
                        except json.JSONDecodeError:
                            pass

    except Exception as e:
        error = str(e)

    elapsed = round(time.time() - start, 1)
    result_dict[key] = {
        "events": events,
        "error": error,
        "elapsed": elapsed,
        "has_error_event": any(e.get("type") == "error" for e in events),
        "has_done_event": any(e.get("type") == "done" for e in events),
        "has_text": any(e.get("type") == "text" for e in events),
    }


def post_json(host, path, body):
    """Simple JSON POST helper."""
    url = f"{host}{path}"
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def get_gunicorn_memory_mb():
    """Return total RSS memory of all gunicorn workers in MB."""
    try:
        result = subprocess.run(
            ["bash", "-c", "ps -o rss= -p $(pgrep -d, -f gunicorn) 2>/dev/null | tr ',' '\n' | awk '{sum+=$1} END {print sum}'"],
            capture_output=True, text=True, timeout=5
        )
        val = result.stdout.strip()
        return round(int(val) / 1024, 1) if val.isdigit() else None
    except Exception:
        return None


def health_check(host):
    """Return True if server is reachable."""
    try:
        with urllib.request.urlopen(f"{host}/api/health", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def print_result(key, r):
    status = PASS if (r["has_done_event"] and not r["has_error_event"] and not r["error"]) else FAIL
    print(f"  {status} {key}: elapsed={r['elapsed']}s | done={r['has_done_event']} | error_event={r['has_error_event']} | net_error={r['error'] or 'none'}")


# ─── TC-1: Two simultaneous PM requests ───────────────────────────────────────

def tc1(host):
    print(f"\n{'='*60}")
    print("TC-1: สอง PM requests พร้อมกัน")
    print("="*60)

    results = {}
    t1 = threading.Thread(target=sse_collect, args=(
        host, "สร้างเอกสารต้อนรับพนักงานใหม่แผนก HR อย่างละเอียด",
        results, "user_a"
    ))
    t2 = threading.Thread(target=sse_collect, args=(
        host, "สร้างรายงานสรุปค่าใช้จ่ายประจำเดือนสำหรับฝ่ายบัญชี",
        results, "user_b"
    ))

    print(f"  {INFO} Starting both requests simultaneously...")
    start = time.time()
    t1.start()
    time.sleep(0.3)   # stagger slightly to avoid exact same timestamp
    t2.start()
    t1.join(timeout=TIMEOUT_PER_REQUEST + 10)
    t2.join(timeout=TIMEOUT_PER_REQUEST + 10)
    total = round(time.time() - start, 1)

    print_result("User A", results.get("user_a", {"has_done_event": False, "has_error_event": True, "error": "timeout", "elapsed": 0}))
    print_result("User B", results.get("user_b", {"has_done_event": False, "has_error_event": True, "error": "timeout", "elapsed": 0}))
    print(f"  {INFO} Total wall-clock time: {total}s")

    ra = results.get("user_a", {})
    rb = results.get("user_b", {})
    passed = (
        ra.get("has_done_event") and not ra.get("has_error_event") and not ra.get("error") and
        rb.get("has_done_event") and not rb.get("has_error_event") and not rb.get("error")
    )
    print(f"\n  Result: {PASS if passed else FAIL}")
    return passed


# ─── TC-2: PM request + workspace switch mid-flight ───────────────────────────

def tc2(host):
    print(f"\n{'='*60}")
    print("TC-2: PM request + workspace switch กลางคัน")
    print("="*60)

    # Ensure workspace B exists
    os.makedirs(WORKSPACE_B, exist_ok=True)

    results = {}
    switch_result = {}

    def run_pm():
        sse_collect(host, "สร้างนโยบายการลาพักร้อนสำหรับพนักงาน อย่างละเอียด", results, "pm")

    def switch_workspace():
        time.sleep(5)   # wait 5s after PM starts, then switch
        print(f"  {WARN} Switching workspace to {WORKSPACE_B} at t=5s...")
        r = post_json(host, "/api/workspace", {"path": WORKSPACE_B})
        switch_result["response"] = r
        print(f"  {INFO} Workspace switch response: {r}")

    t_pm = threading.Thread(target=run_pm)
    t_sw = threading.Thread(target=switch_workspace)

    print(f"  {INFO} Starting PM request, workspace switch will fire at t=5s...")
    t_pm.start()
    t_sw.start()
    t_pm.join(timeout=TIMEOUT_PER_REQUEST + 10)
    t_sw.join(timeout=20)

    pm = results.get("pm", {})
    print_result("PM request", pm)

    # Check: PM should still complete (workspace snapshot taken at start)
    passed = pm.get("has_done_event") and not pm.get("error")
    if passed:
        print(f"  {INFO} PM completed successfully despite workspace switch — snapshot isolation works")
    else:
        print(f"  {WARN} PM failed or hung — may be affected by workspace switch")

    # Restore workspace A
    post_json(host, "/api/workspace", {"path": WORKSPACE_A})
    print(f"  {INFO} Restored workspace to {WORKSPACE_A}")

    print(f"\n  Result: {PASS if passed else FAIL}")
    return passed


# ─── TC-3: Three simultaneous PM requests (rate limit) ────────────────────────

def tc3(host):
    print(f"\n{'='*60}")
    print("TC-3: สาม PM requests พร้อมกัน (rate limit simulation)")
    print("="*60)

    results = {}
    messages = [
        ("user_a", "สร้างสัญญาจ้างงานพนักงานประจำ"),
        ("user_b", "สร้างใบแจ้งหนี้ค่าบริการประจำเดือน"),
        ("user_c", "สร้างรายงานการประเมินผลงานพนักงาน"),
    ]

    threads = []
    for key, msg in messages:
        t = threading.Thread(target=sse_collect, args=(host, msg, results, key))
        threads.append(t)

    print(f"  {INFO} Launching 3 PM requests with 0.5s stagger...")
    for i, t in enumerate(threads):
        t.start()
        if i < len(threads) - 1:
            time.sleep(0.5)

    for t in threads:
        t.join(timeout=TIMEOUT_PER_REQUEST + 10)

    all_passed = True
    for key, _ in messages:
        r = results.get(key, {"has_done_event": False, "has_error_event": True, "error": "timeout", "elapsed": 0})
        print_result(key, r)
        # Pass if done OR got a typed error event (not a hang/500)
        ok = r.get("has_done_event") or r.get("has_error_event")
        if not ok:
            all_passed = False

    if not all_passed:
        print(f"  {WARN} At least one request hung without any event — server may have crashed")

    print(f"\n  Result: {PASS if all_passed else FAIL}")
    return all_passed


# ─── TC-4: Memory leak baseline ───────────────────────────────────────────────

def tc4(host):
    print(f"\n{'='*60}")
    print("TC-4: Memory leak baseline (10 sequential requests)")
    print("="*60)

    mem_before = get_gunicorn_memory_mb()
    if mem_before is None:
        print(f"  {WARN} Cannot read gunicorn memory (not running via gunicorn, or pgrep unavailable)")
        print(f"  {INFO} Skipping memory check — running functional test only")

    print(f"  {INFO} Memory before: {mem_before}MB" if mem_before else f"  {INFO} Memory before: N/A")
    print(f"  {INFO} Running 10 sequential chat requests...")

    errors = 0
    for i in range(10):
        results = {}
        sse_collect(host, f"สวัสดี ทดสอบครั้งที่ {i+1}", results, "req", timeout=60)
        r = results.get("req", {})
        ok = r.get("has_done_event") and not r.get("error")
        print(f"  {'✅' if ok else '❌'} Request {i+1:2d}: {r.get('elapsed',0)}s")
        if not ok:
            errors += 1
        time.sleep(1)

    mem_after = get_gunicorn_memory_mb()
    print(f"  {INFO} Memory after:  {mem_after}MB" if mem_after else f"  {INFO} Memory after:  N/A")

    passed = errors == 0
    if mem_before and mem_after:
        growth = round(mem_after - mem_before, 1)
        leak_ok = growth < 50
        print(f"  {INFO} Memory growth: {growth}MB ({'OK' if leak_ok else 'POSSIBLE LEAK'})")
        passed = passed and leak_ok

    print(f"\n  Result: {PASS if passed else FAIL}")
    return passed


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D2 Concurrency Test")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server URL (default: http://localhost:5000)")
    parser.add_argument("--tc", nargs="+", type=int, choices=[1,2,3,4],
                        default=[1,2,3,4], help="Test cases to run (default: all)")
    args = parser.parse_args()

    host = args.host.rstrip("/")
    print(f"\n🧪 D2 Concurrency Test — {host}")
    print(f"   Running TC: {args.tc}\n")

    # Health check
    print(f"{INFO} Checking server health...")
    if not health_check(host):
        print(f"{FAIL} Server not reachable at {host}")
        print("   ตรวจสอบว่า ./start.sh รันอยู่และ port ถูกต้อง")
        sys.exit(1)
    print(f"{PASS} Server is up\n")

    tc_map = {1: tc1, 2: tc2, 3: tc3, 4: tc4}
    results = {}

    for tc_num in args.tc:
        results[tc_num] = tc_map[tc_num](host)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    for tc_num, passed in results.items():
        print(f"  TC-{tc_num}: {PASS if passed else FAIL}")

    all_passed = all(results.values())
    print(f"\n  Overall: {PASS if all_passed else FAIL}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
