import os
import threading
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")

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
WORKSPACE_PATH = _DEFAULT_WORKSPACE
_workspace_lock = threading.Lock()

# Event bus for workspace changes
_ws_change_queues = {} # workspace_path -> [queue.Queue]
_ws_change_lock = threading.Lock()

# OpenAI Client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
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
