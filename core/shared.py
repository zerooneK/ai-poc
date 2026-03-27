import os
import threading
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")

import logging as _logging
if not OPENROUTER_API_KEY:
    _logging.getLogger(__name__).error(
        "[shared] OPENROUTER_API_KEY is not set — copy .env.example to .env and set your key. All API calls will fail."
    )

_PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Allowed workspace roots
_raw_roots = os.getenv("ALLOWED_WORKSPACE_ROOTS")
if _raw_roots:
    _ALLOWED_ROOTS = [os.path.realpath(p.strip()) for p in _raw_roots.split(",") if p.strip()]
else:
    _ALLOWED_ROOTS = [os.path.realpath(_PROJECT_ROOT)]

# Default workspace
_DEFAULT_WORKSPACE = os.path.abspath(
    os.getenv("WORKSPACE_PATH", os.path.join(_PROJECT_ROOT, "workspace"))
)

# Shared state
# ⚠️  DEPLOYMENT RISK — D3: WORKSPACE_PATH is a single global shared across ALL sessions.
# set_workspace() changes the path for every concurrent user simultaneously.
# Safe usage rule: ALWAYS capture workspace once at request start via get_workspace()
# and pass it as a parameter — NEVER call get_workspace() again inside loops or sub-calls.
# For multi-user production: replace with per-session dict keyed by session_id.
WORKSPACE_PATH = _DEFAULT_WORKSPACE
_workspace_lock = threading.Lock()

# Event bus for workspace changes
_ws_change_queues = {} # workspace_path -> [queue.Queue]
_ws_change_lock = threading.Lock()

# OpenAI Client
import logging as _logging
try:
    _TIMEOUT = float(os.getenv('OPENROUTER_TIMEOUT', '60'))
except ValueError:
    _logging.getLogger(__name__).warning("[shared] Invalid OPENROUTER_TIMEOUT value, defaulting to 60.0")
    _TIMEOUT = 60.0
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=_TIMEOUT,
)

# Temp directory
TEMP_DIR = os.path.abspath(os.path.join(_PROJECT_ROOT, 'temp'))
os.makedirs(TEMP_DIR, exist_ok=True)

def get_model():
    return MODEL

def get_client():
    return client

def get_workspace():
    with _workspace_lock:
        return WORKSPACE_PATH

def set_workspace(path):
    global WORKSPACE_PATH
    with _workspace_lock:
        WORKSPACE_PATH = path

def _notify_workspace_changed(workspace_path: str):
    """Notify all streaming clients watching this workspace."""
    import queue
    with _ws_change_lock:
        queues = _ws_change_queues.get(workspace_path, [])
        for q in queues:
            try:
                q.put_nowait('changed')
            except queue.Full:
                pass
