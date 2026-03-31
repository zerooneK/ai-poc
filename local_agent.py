"""
Local File Agent — AI Assistant POC  v0.22.0
=============================================
รัน script นี้บนเครื่องของคุณ (Windows CMD/PowerShell) เพื่อให้ AI
สามารถสร้าง / แก้ไข / ลบไฟล์ใน directory ที่กำหนดได้โดยตรง

วิธีใช้:
  python local_agent.py
  python local_agent.py C:\\Users\\name\\ai-workspace
  python local_agent.py --port 7000 C:\\Users\\name\\ai-workspace

Endpoints:
  GET  /health        — ตรวจสอบว่า agent รันอยู่ + workspace ปัจจุบัน
  POST /files         — จัดการไฟล์ (ดูฟิลด์ action ด้านล่าง)

POST /files body (JSON):
  { "action": "list" }
  { "action": "create", "filename": "doc.md", "content": "..." }
  { "action": "read",   "filename": "doc.md" }
  { "action": "update", "filename": "doc.md", "content": "..." }
  { "action": "delete", "filename": "doc.md" }

Security:
  - ออกนอก workspace ไม่ได้เด็ดขาด (path traversal blocked)
  - รับ request จาก localhost เท่านั้น
"""

import argparse
import json
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

DEFAULT_PORT = 7000
DEFAULT_WORKSPACE = os.path.join(os.path.expanduser("~"), "ai-workspace")

# Origins allowed to call this agent.
# Set LOCAL_AGENT_ALLOWED_ORIGINS env var to override (comma-separated).
_ALLOWED_ORIGINS: set = {
    o.strip()
    for o in os.getenv(
        "LOCAL_AGENT_ALLOWED_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000",
    ).split(",")
    if o.strip()
}

# ─── Sandbox + File Operations ────────────────────────────────────────────────

def _validate_path(workspace: str, filename: str) -> str:
    """Resolve path และตรวจสอบว่า filename อยู่ใน workspace เท่านั้น
    Raises ValueError ถ้าพยายาม path traversal (../../ ฯลฯ)"""
    workspace_abs = str(Path(workspace).resolve())
    target = str(Path(workspace_abs, filename).resolve())
    try:
        common = os.path.commonpath([workspace_abs, target])
        if common != workspace_abs:
            raise ValueError(f"ไม่อนุญาต: '{filename}' อยู่นอก workspace")
    except ValueError:
        raise ValueError(f"ไม่อนุญาต: '{filename}' อยู่นอก workspace")
    return target


def fs_list_files(workspace: str) -> list:
    workspace_abs = os.path.abspath(workspace)
    if not os.path.isdir(workspace_abs):
        return []
    result = []
    try:
        for entry in sorted(os.scandir(workspace_abs), key=lambda e: e.name):
            if entry.is_file():
                stat = entry.stat()
                result.append({
                    "name": entry.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
    except OSError:
        pass
    return result


def fs_create_file(workspace: str, filename: str, content: str) -> str:
    path = _validate_path(workspace, filename)
    if os.path.exists(path):
        raise FileExistsError(f"ไฟล์ '{filename}' มีอยู่แล้ว ใช้ action=update เพื่อแก้ไข")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ สร้างไฟล์ '{filename}' สำเร็จ ({len(content)} ตัวอักษร)"


def fs_read_file(workspace: str, filename: str) -> str:
    path = _validate_path(workspace, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"ไม่พบไฟล์ '{filename}'")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def fs_update_file(workspace: str, filename: str, content: str) -> str:
    path = _validate_path(workspace, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ อัปเดตไฟล์ '{filename}' สำเร็จ ({len(content)} ตัวอักษร)"


def fs_delete_file(workspace: str, filename: str) -> str:
    path = _validate_path(workspace, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"ไม่พบไฟล์ '{filename}'")
    os.remove(path)
    return f"✅ ลบไฟล์ '{filename}' สำเร็จ"

# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class AgentHandler(BaseHTTPRequestHandler):

    workspace = None  # set before server starts

    # ── CORS ──────────────────────────────────────────────────────────────────

    def _origin_allowed(self) -> bool:
        """Return True if request Origin is in the allowlist or absent (curl/scripts)."""
        origin = self.headers.get("Origin", "")
        return (not origin) or (origin in _ALLOWED_ORIGINS)

    def _add_cors_headers(self):
        origin = self.headers.get("Origin", "")
        if origin in _ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        """Preflight request สำหรับ CORS"""
        if not self._origin_allowed():
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        if self.path == "/health":
            self._send_json({
                "status": "ok",
                "workspace": AgentHandler.workspace,
                "port": self.server.server_address[1],
                "version": "0.22.0",
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        if self.path != "/files":
            self._send_json({"error": "Not found"}, 404)
            return

        if not self._origin_allowed():
            self._send_json({"ok": False, "error": "Origin not allowed"}, 403)
            return

        # อ่าน body
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        action   = data.get("action", "")
        filename = data.get("filename", "").strip()
        content  = data.get("content", "")
        ws       = AgentHandler.workspace

        try:
            if action == "list":
                files = fs_list_files(ws)
                self._send_json({"ok": True, "files": files})

            elif action == "create":
                if not filename:
                    self._send_json({"ok": False, "error": "ต้องระบุ filename"}, 400)
                    return
                msg = fs_create_file(ws, filename, content)
                self._send_json({"ok": True, "message": msg, "filename": filename})

            elif action == "read":
                if not filename:
                    self._send_json({"ok": False, "error": "ต้องระบุ filename"}, 400)
                    return
                text = fs_read_file(ws, filename)
                self._send_json({"ok": True, "content": text, "filename": filename})

            elif action == "update":
                if not filename:
                    self._send_json({"ok": False, "error": "ต้องระบุ filename"}, 400)
                    return
                msg = fs_update_file(ws, filename, content)
                self._send_json({"ok": True, "message": msg, "filename": filename})

            elif action == "delete":
                if not filename:
                    self._send_json({"ok": False, "error": "ต้องระบุ filename"}, 400)
                    return
                msg = fs_delete_file(ws, filename)
                self._send_json({"ok": True, "message": msg, "filename": filename})

            else:
                self._send_json({"ok": False, "error": f"ไม่รู้จัก action '{action}'"}, 400)

        except (ValueError, FileNotFoundError, FileExistsError) as e:
            self._send_json({"ok": False, "error": str(e)}, 400)
        except Exception as e:
            self._send_json({"ok": False, "error": f"เกิดข้อผิดพลาด: {e}"}, 500)

    # ── Helper ────────────────────────────────────────────────────────────────

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}]  {fmt % args}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Local File Agent — AI Assistant POC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="ตัวอย่าง:\n  python local_agent.py\n  python local_agent.py C:\\Users\\name\\ai-workspace\n  python local_agent.py --port 8000 D:\\my-docs"
    )
    parser.add_argument("workspace", nargs="?", default=DEFAULT_WORKSPACE,
                        help=f"Directory ที่ agent จะทำงาน (default: {DEFAULT_WORKSPACE})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    port      = args.port

    # สร้าง workspace ถ้ายังไม่มี
    os.makedirs(workspace, exist_ok=True)

    AgentHandler.workspace = workspace

    server = HTTPServer(("localhost", port), AgentHandler)

    print()
    print("=" * 52)
    print("   AI Assistant — Local File Agent  v0.22.0")
    print("=" * 52)
    print(f"   Workspace : {workspace}")
    print(f"   Port      : {port}")
    print(f"   URL       : http://localhost:{port}/health")
    print("=" * 52)
    print("   กด Ctrl+C เพื่อหยุด")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  หยุดการทำงานแล้ว")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
