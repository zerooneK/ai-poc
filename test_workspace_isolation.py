#!/usr/bin/env python
"""
Session workspace isolation checks for the Flask API.

Run with the server already running on localhost:5000.
Exit code 0 = all checks pass, 1 = any check fails.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 20
TH_SAVE = "\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.join(PROJECT_ROOT, "workspace")
SESSION_A = "workspace-test-a"
SESSION_B = "workspace-test-b"
RUN_ID = str(os.getpid())
WORKSPACE_A = os.path.join(WORKSPACE_ROOT, f"session_workspace_a_{RUN_ID}")
WORKSPACE_B = os.path.join(WORKSPACE_ROOT, f"session_workspace_b_{RUN_ID}")
DOC_A = "Workspace isolation document for session A"
DOC_B = "Workspace isolation document for session B"


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


def _parse_json(raw: str) -> dict:
    return json.loads(raw or "{}")


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


def _set_workspace(session_id: str, workspace_path: str) -> bool:
    status, _ = _request_json(
        "POST",
        "/api/workspace",
        {"path": workspace_path, "session_id": session_id},
    )
    return status == 200


def _reset_workspace_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    for entry in os.scandir(path):
        if entry.is_file():
            os.remove(entry.path)


def _save_pending_doc(session_id: str, content: str) -> bool:
    status, raw = _request_json(
        "POST",
        "/api/chat",
        {
            "message": TH_SAVE,
            "session_id": session_id,
            "pending_doc": content,
            "pending_agent": "hr",
        },
    )
    events = _parse_sse(raw)
    has_done = any(event.get("type") == "done" for event in events)
    has_error = any(event.get("type") in {"error", "save_failed"} for event in events)
    return status == 200 and has_done and not has_error


def _list_files(session_id: str) -> list[dict]:
    status, raw = _request_json("GET", f"/api/files?session_id={session_id}")
    if status != 200:
        return []
    return _parse_json(raw).get("files", [])


def _preview(session_id: str, filename: str) -> tuple[int, dict]:
    status, raw = _request_json(
        "GET",
        f"/api/preview?file={urllib.parse.quote(filename)}&session_id={session_id}",
    )
    try:
        return status, _parse_json(raw)
    except json.JSONDecodeError:
        return status, {}


def _delete(session_id: str, filename: str) -> int:
    status, _ = _request_json(
        "POST",
        "/api/delete",
        {"filename": filename, "session_id": session_id},
    )
    return status


def _print_result(name: str, ok: bool, detail: str) -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return ok


def check_workspace_isolation() -> bool:
    _reset_workspace_dir(WORKSPACE_A)
    _reset_workspace_dir(WORKSPACE_B)

    setup_ok = _set_workspace(SESSION_A, WORKSPACE_A) and _set_workspace(SESSION_B, WORKSPACE_B)
    if not setup_ok:
        return _print_result("workspace setup", False, "failed to assign workspaces")

    if not _save_pending_doc(SESSION_A, DOC_A):
        return _print_result("save session A", False, "pending_doc save failed")
    if not _save_pending_doc(SESSION_B, DOC_B):
        return _print_result("save session B", False, "pending_doc save failed")

    files_a = _list_files(SESSION_A)
    files_b = _list_files(SESSION_B)
    if len(files_a) != 1 or len(files_b) != 1:
        return _print_result("session file lists", False, f"session_a={len(files_a)}, session_b={len(files_b)}")

    filename_a = files_a[0]["name"]
    filename_b = files_b[0]["name"]

    preview_a_status, preview_a = _preview(SESSION_A, filename_a)
    preview_b_status, preview_b = _preview(SESSION_B, filename_b)
    content_ok = preview_a_status == 200 and DOC_A in preview_a.get("content", "")
    content_b_ok = preview_b_status == 200 and DOC_B in preview_b.get("content", "")
    if not content_ok or not content_b_ok:
        return _print_result(
            "preview isolation",
            False,
            f"session_a_status={preview_a_status}, session_b_status={preview_b_status}",
        )

    delete_status = _delete(SESSION_A, filename_a)
    files_a_after = _list_files(SESSION_A)
    files_b_after = _list_files(SESSION_B)
    preview_b_after_delete_status, preview_b_after_delete = _preview(SESSION_B, filename_b)
    delete_ok = (
        delete_status == 200
        and not files_a_after
        and len(files_b_after) == 1
        and files_b_after[0]["name"] == filename_b
        and preview_b_after_delete_status == 200
        and DOC_B in preview_b_after_delete.get("content", "")
    )
    return _print_result(
        "delete isolation",
        delete_ok,
        f"delete_status={delete_status}, session_a={len(files_a_after)}, session_b={len(files_b_after)}",
    )


def main() -> int:
    print("Workspace Isolation Test")
    print("=" * 60)
    ok = check_workspace_isolation()
    print("=" * 60)
    print("Summary: 1/1 checks passed" if ok else "Summary: 0/1 checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
