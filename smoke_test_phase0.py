#!/usr/bin/env python
"""
Phase 0 smoke test for the Flask app.

Goals:
- avoid external test dependencies like `requests`
- avoid Windows shell encoding issues with Thai confirmation keywords
- verify the critical hardening paths added in Phase 0

Run:
    python smoke_test_phase0.py
"""

from __future__ import annotations

import json
import socket
import sys
import time
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 20
BASIC_CHAT_RETRIES = 3
BASIC_CHAT_RETRY_DELAY_SECONDS = 1

TH_SAVE = "\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01"
TH_DISCARD = "\u0e22\u0e01\u0e40\u0e25\u0e34\u0e01"
WORKSPACE_PATH = r"D:\ai-poc\workspace"
BLOCKED_WORKSPACE_PATH = r"C:\Windows\Temp"


def _request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except TimeoutError as exc:
        return 0, f"transport_timeout:{exc}"
    except socket.timeout as exc:
        return 0, f"transport_timeout:{exc}"
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return 0, f"transport_error:{reason}"


def _parse_sse(raw: str) -> list[dict]:
    events: list[dict] = []
    for block in raw.split("\n\n"):
        if not block.startswith("data: "):
            continue
        try:
            events.append(json.loads(block[6:]))
        except json.JSONDecodeError:
            continue
    return events


def _print_result(name: str, ok: bool, detail: str) -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return ok


def _summarize_events(events: list[dict]) -> str:
    event_types = sorted({event.get("type") for event in events if event.get("type")})
    errors = [event.get("message", "") for event in events if event.get("type") == "error"]
    detail = f"events={event_types}"
    if errors:
        detail += f", errors={errors[:2]}"
    return detail


def check_health() -> bool:
    status, raw = _request_json("GET", "/api/health")
    ok = status == 200
    detail = f"status={status}"
    if ok:
        try:
            data = json.loads(raw)
            detail = f"status={status}, workspace={data.get('workspace')}"
        except json.JSONDecodeError:
            detail = f"status={status}, invalid JSON body"
            ok = False
    return _print_result("health", ok, detail)


def check_workspace_guard() -> bool:
    allowed_status, _ = _request_json("POST", "/api/workspace", {"path": WORKSPACE_PATH})
    blocked_status, _ = _request_json("POST", "/api/workspace", {"path": BLOCKED_WORKSPACE_PATH})
    ok = allowed_status == 200 and blocked_status == 400
    detail = f"allowed={allowed_status}, blocked={blocked_status}"
    return _print_result("workspace guard", ok, detail)


def check_basic_chat() -> bool:
    last_detail = "no attempts"
    for attempt in range(1, BASIC_CHAT_RETRIES + 1):
        status, raw = _request_json("POST", "/api/chat", {"message": "test smoke"})
        events = _parse_sse(raw)
        event_types = {event.get("type") for event in events}
        ok = status == 200 and {"agent", "text", "done"}.issubset(event_types)
        last_detail = f"attempt={attempt}, http={status}, {_summarize_events(events)}"
        if ok:
            return _print_result("basic chat", True, last_detail)

        # Retry only when the runtime responded but the model/tool path flaked transiently.
        transient_error = status == 200 and "agent" in event_types and "error" in event_types
        if not transient_error or attempt == BASIC_CHAT_RETRIES:
            break
        time.sleep(BASIC_CHAT_RETRY_DELAY_SECONDS)

    detail = f"{last_detail}, retries={BASIC_CHAT_RETRIES}"
    return _print_result("basic chat", False, detail)


def check_thai_save_flow() -> bool:
    status, raw = _request_json(
        "POST",
        "/api/chat",
        {
            "message": TH_SAVE,
            "pending_doc": "Phase 0 smoke test document",
            "pending_agent": "hr",
        },
    )
    events = _parse_sse(raw)
    event_types = {event.get("type") for event in events}
    has_tool_result = any(event.get("type") == "tool_result" and event.get("tool") == "create_file" for event in events)
    has_error = any(event.get("type") == "error" for event in events)
    ok = status == 200 and has_tool_result and "done" in event_types and not has_error
    detail = f"http={status}, tool_result={has_tool_result}, error={has_error}"
    return _print_result("thai save confirmation", ok, detail)


def check_thai_discard_flow() -> bool:
    status, raw = _request_json(
        "POST",
        "/api/chat",
        {
            "message": TH_DISCARD,
            "pending_doc": "Phase 0 smoke test document",
            "pending_agent": "hr",
        },
    )
    events = _parse_sse(raw)
    texts = [event.get("content", "") for event in events if event.get("type") == "text"]
    has_done = any(event.get("type") == "done" for event in events)
    has_cancel_message = any("\u0e22\u0e01\u0e40\u0e25\u0e34\u0e01\u0e40\u0e2d\u0e01\u0e2a\u0e32\u0e23" in text for text in texts)
    ok = status == 200 and has_done and has_cancel_message
    detail = f"http={status}, done={has_done}, cancel_text={has_cancel_message}"
    return _print_result("thai discard confirmation", ok, detail)


def main() -> int:
    checks = [
        check_health,
        check_workspace_guard,
        check_basic_chat,
        check_thai_save_flow,
        check_thai_discard_flow,
    ]

    print("Phase 0 Smoke Test")
    print("=" * 60)
    results = [check() for check in checks]
    passed = sum(1 for ok in results if ok)
    total = len(results)
    print("=" * 60)
    print(f"Summary: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
