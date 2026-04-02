import os
import threading
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

# Workspace state file — persists last-used workspace across server restarts
_WORKSPACE_STATE_FILE = os.path.join(_PROJECT_ROOT, 'data', '.workspace_state')

def _load_persisted_workspace() -> str:
    """Load last workspace path from state file. Falls back to default."""
    try:
        with open(_WORKSPACE_STATE_FILE, 'r', encoding='utf-8') as f:
            path = f.read().strip()
        if path and os.path.isdir(path):
            return path
    except (OSError, ValueError):
        pass
    return _DEFAULT_WORKSPACE

def _persist_workspace(path: str):
    """Save current workspace path to state file."""
    try:
        os.makedirs(os.path.dirname(_WORKSPACE_STATE_FILE), exist_ok=True)
        with open(_WORKSPACE_STATE_FILE, 'w', encoding='utf-8') as f:
            f.write(path)
    except OSError as e:
        _logging.getLogger(__name__).warning("[shared] Failed to persist workspace path: %s", e)

# Shared state
# ⚠️  DEPLOYMENT RISK — D3: WORKSPACE_PATH is a single global shared across ALL sessions.
# set_workspace() changes the path for every concurrent user simultaneously.
# Safe usage rule: ALWAYS capture workspace once at request start via get_workspace()
# and pass it as a parameter — NEVER call get_workspace() again inside loops or sub-calls.
# For multi-user production: replace with per-session dict keyed by session_id.
WORKSPACE_PATH = _load_persisted_workspace()
_workspace_lock = threading.Lock()

# Per-session workspace state (thread-safe, persisted across restarts)
_SESSION_WS_STATE_FILE = os.path.join(_PROJECT_ROOT, 'data', '.session_workspaces.json')
_session_ws_lock = threading.Lock()


def _load_session_workspaces() -> dict:
    """Load persisted session→workspace mappings. Drops entries whose directories no longer exist."""
    try:
        with open(_SESSION_WS_STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items()
                if isinstance(k, str) and isinstance(v, str) and os.path.isdir(v)}
    except (OSError, ValueError):
        return {}


def _persist_session_workspaces(snapshot: dict) -> None:
    """Write current session→workspace mappings to disk (called under _session_ws_lock)."""
    try:
        os.makedirs(os.path.dirname(_SESSION_WS_STATE_FILE), exist_ok=True)
        with open(_SESSION_WS_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2)
    except OSError as e:
        _logging.getLogger(__name__).warning("[shared] Failed to persist session workspaces: %s", e)


_session_workspaces: dict = _load_session_workspaces()


def get_session_workspace(session_id: str) -> str:
    """Return the workspace path for a specific session, falling back to the global."""
    with _session_ws_lock:
        return _session_workspaces.get(session_id, WORKSPACE_PATH)


def set_session_workspace(session_id: str, path: str) -> None:
    """Set the workspace path for a specific session and persist to disk."""
    with _session_ws_lock:
        _session_workspaces[session_id] = path
        _persist_session_workspaces(dict(_session_workspaces))


def remove_session_workspace(session_id: str) -> None:
    """Remove a session-specific workspace mapping and persist to disk."""
    with _session_ws_lock:
        _session_workspaces.pop(session_id, None)
        _persist_session_workspaces(dict(_session_workspaces))

# Event bus for workspace changes
_ws_change_queues = {} # workspace_path -> [queue.Queue]
_ws_change_lock = threading.Lock()

# OpenAI Client — lazy-initialized to fail fast if key is missing
import logging as _logging
try:
    _TIMEOUT = float(os.getenv('OPENROUTER_TIMEOUT', '60'))
except ValueError:
    _logging.getLogger(__name__).warning("[shared] Invalid OPENROUTER_TIMEOUT value, defaulting to 60.0")
    _TIMEOUT = 60.0

_client = None
_client_lock = threading.Lock()

def get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                if not OPENROUTER_API_KEY:
                    raise RuntimeError("OPENROUTER_API_KEY is not set. Copy .env.example to .env and set your key.")
                from openai import OpenAI
                _client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY,
                    timeout=_TIMEOUT,
                )
    return _client

# Temp directory
TEMP_DIR = os.path.abspath(os.path.join(_PROJECT_ROOT, 'temp'))
os.makedirs(TEMP_DIR, exist_ok=True)

# ── Output token limits (tune per model in .env) ──────────────────────────────
# AGENT_MAX_TOKENS   — document generation agents (HR, Accounting, Document, etc.)
# CHAT_MAX_TOKENS    — chat / advisory responses
# ORCHESTRATOR_MAX_TOKENS — orchestrator JSON routing (keep low)
AGENT_MAX_TOKENS        = int(os.getenv('AGENT_MAX_TOKENS',        '32000'))
CHAT_MAX_TOKENS         = int(os.getenv('CHAT_MAX_TOKENS',         '8000'))
ORCHESTRATOR_MAX_TOKENS = int(os.getenv('ORCHESTRATOR_MAX_TOKENS', '1024'))

def get_model():
    return MODEL

def get_workspace():
    with _workspace_lock:
        return WORKSPACE_PATH

def set_workspace(path):
    global WORKSPACE_PATH
    with _workspace_lock:
        WORKSPACE_PATH = path
    _persist_workspace(path)

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
