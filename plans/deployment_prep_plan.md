# Deployment Preparation Plan

**Project:** AI Assistant POC — Internal HR/Accounting/PM System
**Date:** 2026-03-27 (พ.ศ. 2569)
**Status:** DRAFT — Not cleared for production
**Plan Version:** 1.0
**Author:** Technical Planner (Claude Sonnet 4.6)

---

## Summary Table

| # | Item | Priority | Current Status | Version Target | Execution Order |
|---|------|----------|---------------|----------------|-----------------|
| D1 | Switch Flask dev server to gunicorn + gevent | CRITICAL | ✅ DONE `v0.18.0` | v0.18.0 | 1st |
| D2 | Concurrency test — PM flow with 2+ simultaneous users | CRITICAL | No concurrency test exists | v0.16.0 | 2nd (after D1) |
| D3 | Session isolation — workspace is a single global variable | HIGH | ✅ DONE `v0.20.0` — audited safe + guard comments added | v0.20.0 | 3rd |
| D4 | Rate limiting on /api/chat | HIGH | ✅ DONE `v0.19.0` | v0.19.0 | 1st (parallel with D1) |
| D5 | Environment and secrets checklist for production | HIGH | ✅ DONE `v0.18.0` | v0.18.0 | 1st (parallel with D1) |

---

## D1 — Switch Flask Dev Server to Gunicorn + Gevent

**Priority:** CRITICAL
**Estimated Effort:** 2–3 hours (High confidence)
**Execution Order:** Must be done before any load or concurrency testing

### Evidence

File: `start.sh`, line 42

```bash
python app.py
```

File: `app.py`, lines 565–566

```python
if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG','').lower() in {'1','true'}, host=os.getenv('FLASK_HOST','0.0.0.0'), port=5000, threaded=True)
```

The application is launched directly via `python app.py`, which invokes Werkzeug's built-in development server with `threaded=True`. This server is documented by Flask/Werkzeug as unsuitable for production. It is single-process, uses Python threads (GIL-bound), cannot handle concurrent SSE streaming connections efficiently, and provides no worker process management or automatic restart on crash.

The `threaded=True` flag allows concurrent requests within one OS process, but each SSE streaming connection holds a thread open for its entire duration. Under the GIL, this collapses to near-serial execution for CPU-bound work. For AI streaming responses — which can run for 30–90 seconds each — this is a critical bottleneck.

### Problem Description

Every `/api/chat` call opens an SSE generator that streams tokens from the OpenRouter API for as long as the model responds. With `threaded=True` and Werkzeug, two concurrent users will share a single process and a single GIL. The second user's request blocks behind the first user's AI response. With gevent, each SSE connection becomes a lightweight greenlet that yields to the event loop during I/O (the OpenRouter HTTP call), allowing true concurrency without OS thread overhead.

Additionally, Werkzeug's dev server will print a warning and refuse to guarantee correct behavior in production. It does not manage worker crashes, memory leaks, or graceful restarts.

### Fix — Required Changes

**Step 1: Add gunicorn and gevent to requirements.txt**

Add these two lines to `requirements.txt`:

```
gunicorn
gevent
```

**Step 2: Create `gunicorn.conf.py` in the project root**

```python
# gunicorn.conf.py
import os

# Worker class — gevent enables async I/O for SSE streaming
worker_class = "gevent"

# Number of workers: 1 per CPU core is standard for gevent
# For POC/demo: 2 workers is safe on a 2–4 core machine
workers = int(os.getenv("GUNICORN_WORKERS", "2"))

# Greenlets per worker — each SSE connection = 1 greenlet
# 50 concurrent SSE streams per worker is conservative
worker_connections = int(os.getenv("GUNICORN_CONNECTIONS", "50"))

# Bind address
bind = f"{os.getenv('FLASK_HOST', '0.0.0.0')}:{os.getenv('FLASK_PORT', '5000')}"

# Timeouts — AI responses can take 60–90s; set higher than OPENROUTER_TIMEOUT
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = 5

# Logging
accesslog = "-"   # stdout
errorlog  = "-"   # stderr
loglevel  = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Graceful restart window
graceful_timeout = 30
```

**Step 3: Update `start.sh` — replace line 42**

Replace:
```bash
python app.py
```

With:
```bash
export PYTHONIOENCODING=utf-8
./venv/bin/gunicorn --config gunicorn.conf.py "app:app"
```

The full updated `start.sh` run block (lines 40–42) becomes:

```bash
# Run via gunicorn + gevent (production-safe, SSE-compatible)
export PYTHONIOENCODING=utf-8
./venv/bin/gunicorn --config gunicorn.conf.py "app:app"
```

**Step 4: Keep the `if __name__ == '__main__':` block in app.py for local debug**

No change needed to `app.py` line 565–566. That block is only used when a developer runs `python app.py` directly for debugging. Gunicorn imports `app:app` directly and bypasses that block entirely.

### Acceptance Checklist

- [ ] `gunicorn` and `gevent` are listed in `requirements.txt`
- [ ] `gunicorn.conf.py` exists in the project root with all values configurable via environment variables
- [ ] `start.sh` runs `gunicorn --config gunicorn.conf.py "app:app"` not `python app.py`
- [ ] Server starts and responds at `http://localhost:5000/api/health`
- [ ] SSE stream from `/api/chat` delivers tokens to the browser without hanging
- [ ] Two simultaneous `/api/chat` POST requests both receive streamed responses (not one waiting for the other)
- [ ] `GUNICORN_WORKERS`, `GUNICORN_CONNECTIONS`, `GUNICORN_TIMEOUT` are documented in `.env.example`

### Definition of Done

```
DONE when:
  All checklist items above pass
  curl http://localhost:5000/api/health returns {"status": "ok"} after gunicorn start
  Two concurrent SSE clients both receive streaming output simultaneously (verified by test D2)
  gunicorn process is running (not python app.py) — verified with: ps aux | grep gunicorn

NOT DONE if:
  start.sh still calls python app.py
  gunicorn starts but SSE stream hangs after the first response chunk
  GUNICORN_* variables are hardcoded in gunicorn.conf.py instead of env-driven
```

### Fallback Plan

```
If gevent causes import conflicts with existing libraries (watchdog, weasyprint):
  Fallback: Use worker_class = "gthread" with threads = 4
  Trade-off: gthread uses OS threads not greenlets — less concurrent SSE capacity
             (~20 concurrent SSE connections per worker instead of 50)
  Trigger: gunicorn fails to start, or SSE stream drops after first chunk
  Decision Owner: Backend developer
```

### Scaling Consideration

```
Current (after fix): 2 workers x 50 greenlets = ~100 concurrent SSE connections
Bottleneck at: ~100 concurrent SSE connections (greenlet limit per worker)
Mitigation: Increase GUNICORN_WORKERS and GUNICORN_CONNECTIONS via env
Future-safe: Yes — gunicorn config is fully externalized; scaling is an env change
```

---

## D2 — Concurrency Test: PM Flow with 2+ Simultaneous Users

**Priority:** CRITICAL
**Estimated Effort:** 3–4 hours to write and run (Medium confidence — depends on D1 being done first)
**Execution Order:** After D1. Cannot be tested meaningfully on the Werkzeug dev server.
**Depends On:** D1 (gunicorn + gevent must be running)

### Evidence

File: `app.py`, lines 423–460 (PM multi-agent loop)

```python
if agent_type == 'pm':
    subtasks = agent_instance.plan(user_input, conversation_history)
    ...
    for i, subtask in enumerate(subtasks):
        sub_agent_type = subtask.get('agent', 'hr')
        sub_task_desc = subtask.get('task', user_input)
        sub_agent = AgentFactory.get_agent(sub_agent_type)
        ...
        for chunk in sub_agent.stream_response(f"[PM_SUBTASK]\n{sub_task_desc}", max_tokens=10000):
            yield format_sse({'type': 'text', 'content': chunk})
```

File: `core/shared.py`, lines 33 and 63–70

```python
# Line 33 — module-level global
WORKSPACE_PATH = _DEFAULT_WORKSPACE

def get_workspace():
    with _workspace_lock:
        return WORKSPACE_PATH

def set_workspace(path):
    global WORKSPACE_PATH
    with _workspace_lock:
        WORKSPACE_PATH = path
```

File: `app.py`, line 365

```python
workspace = get_workspace()
```

The PM flow executes 2–4 sequential sub-agent calls, each making a separate OpenRouter API streaming request. Each sub-agent call can take 20–60 seconds. The total wall-clock time for one PM request is therefore 60–240 seconds. If two users trigger PM requests simultaneously, both read from the same `WORKSPACE_PATH` global at line 365. If either user's session changes the workspace (via `/api/workspace` POST), the second user's in-flight PM loop will silently start writing to the new workspace path — corrupting their output.

### Problem Description

The concurrency risk has two distinct layers:

**Layer 1 — Resource contention at the OpenRouter API:** Two simultaneous PM requests generate 4–8 concurrent streaming API calls. OpenRouter enforces per-key rate limits. Two users doing PM work at the same time may hit those limits, causing one sub-agent stream to receive a `RateLimitError`.

**Layer 2 — Shared WORKSPACE_PATH global (see also D3):** The `workspace` variable captured at line 365 (`workspace = get_workspace()`) is a snapshot of the global at request-start time. However, if `/api/workspace POST` is called by any session during the PM loop's execution, `WORKSPACE_PATH` changes. Subsequent tool calls in the same loop will use `get_workspace()` again (or the already-snapshotted value) inconsistently.

### Concurrency Test Plan

Create a test script `test_concurrency_pm.py` with the following test cases:

**TC-1: Two simultaneous PM requests, different inputs**

```
Scenario: User A sends "สร้างเอกสารต้อนรับพนักงานใหม่" and User B sends
          "สร้างรายงานการประชุมประจำเดือน" at the same time (within 1 second)
Expected: Both SSE streams deliver tokens; both complete without error
Fail condition: Either stream produces {"type": "error"} or hangs >180s
```

**TC-2: PM request during active workspace switch**

```
Scenario: User A starts a PM request. While it is running (5s after start),
          User B calls POST /api/workspace with a different workspace path.
Expected: User A's PM request completes against the workspace captured at start.
          Documents are saved to the correct workspace.
Fail condition: User A's documents appear in User B's workspace, or save fails.
```

**TC-3: Rate limit simulation**

```
Scenario: Three simultaneous PM requests (3 users, each triggering 2–3 sub-agents
          = 6–9 concurrent OpenRouter streaming calls)
Expected: All three complete; any RateLimitError is caught and returned as
          {"type": "error"} SSE event with a user-friendly message (Thai)
Fail condition: Server returns HTTP 500 or silent hang with no error message
```

**TC-4: Memory leak baseline**

```
Scenario: Run 10 sequential PM requests (not concurrent) and measure RSS memory
          before and after using: ps -o rss= -p $(pgrep -f gunicorn) | awk '{sum+=$1} END {print sum}'
Expected: Memory growth < 50MB across 10 requests (no unbounded accumulation)
Fail condition: Memory grows by >5MB per request
```

### Acceptance Checklist

- [ ] TC-1 passes: both SSE streams complete successfully when sent concurrently
- [ ] TC-2 passes: workspace captured at request-start is used for the full PM loop duration
- [ ] TC-3 passes: RateLimitError from OpenRouter is surfaced as a typed SSE error event (not HTTP 500)
- [ ] TC-4 passes: no memory leak pattern after 10 sequential PM requests
- [ ] Test script `test_concurrency_pm.py` is committed to the repository

### Definition of Done

```
DONE when:
  All four test cases pass
  Results are documented in this plan under a "Test Results" subsection
  Any failures found have corresponding bug entries in bug_fix_plan.md

NOT DONE if:
  Tests were only run on the Werkzeug dev server (must run on gunicorn + gevent)
  TC-2 workspace isolation failure is discovered but not tracked
  Memory test was skipped
```

### Fallback Plan

```
If TC-2 (workspace switch during PM) fails and a fix is not straightforward:
  Fallback: Add a per-request workspace snapshot passed as a parameter through
            the entire PM call chain instead of re-calling get_workspace() inside loops
  Trade-off: Requires changes to AgentFactory and sub-agent signatures
  Trigger: TC-2 fails to produce documents in the correct workspace
  Decision Owner: Backend developer
```

### Scaling Consideration

```
Current: 2 gunicorn workers x 50 greenlets; PM uses 2–4 sub-agents sequentially
Bottleneck at: ~5 simultaneous PM users (10–20 concurrent OpenRouter streams hits rate limits)
Mitigation: Implement a per-request semaphore limiting concurrent PM sub-agent calls;
            add retry with exponential backoff on RateLimitError
Future-safe: No — the sequential sub-agent design in the PM loop must become async
             (parallel sub-agents via asyncio or thread pool) to serve >5 concurrent PM users
```

---

## D3 — Session Isolation: Workspace is a Global Variable

**Priority:** HIGH
**Estimated Effort:** 4–8 hours for proper fix; 1 hour to document and add guard (Medium confidence)
**Execution Order:** After D2 (so the test reveals the full scope of the problem first)

### Evidence

File: `core/shared.py`, lines 33–70

```python
# Line 33 — single module-level global shared across ALL requests and sessions
WORKSPACE_PATH = _DEFAULT_WORKSPACE

def get_workspace():
    with _workspace_lock:
        return WORKSPACE_PATH        # returns the same path for every session

def set_workspace(path):
    global WORKSPACE_PATH           # changes the path for every session simultaneously
    with _workspace_lock:
        WORKSPACE_PATH = path
```

File: `app.py`, line 365 (inside the `/api/chat` SSE generator)

```python
workspace = get_workspace()
```

File: `app.py`, lines 483–490 (`/api/workspace POST` — changes the global)

```python
@app.route('/api/workspace', methods=['POST'])
def set_workspace_route():
    ...
    set_workspace(new_path)          # this changes WORKSPACE_PATH for ALL active sessions
```

`WORKSPACE_PATH` is a single module-level variable in `core/shared.py`. The `_workspace_lock` only prevents a race condition during the read/write operation itself — it does not provide per-session isolation. Any call to `set_workspace()` instantly changes the workspace for every currently-active SSE streaming connection.

### Problem Description

Consider this sequence with two users:

1. User A selects workspace `/workspace/project-alpha` via the UI. `set_workspace()` is called. `WORKSPACE_PATH = /workspace/project-alpha`.
2. User A starts a PM request. The generator captures `workspace = get_workspace()` → `/workspace/project-alpha`.
3. User B selects workspace `/workspace/project-beta`. `set_workspace()` is called. `WORKSPACE_PATH = /workspace/project-beta`.
4. User A's PM sub-agent loop calls `get_workspace()` again inside a tool call → now returns `/workspace/project-beta`.
5. User A's documents are silently saved to `/workspace/project-beta`.

This is a data corruption scenario. At the POC stage with one user this is invisible, but with two concurrent users it will cause document misrouting.

### Fix — Required Changes

**Minimum viable fix (document + guard):** Add a comment block in `core/shared.py` that explicitly marks `WORKSPACE_PATH` as a deployment risk and freeze workspace resolution to the value captured at request-start within the SSE generator.

The `/api/chat` generator already captures `workspace = get_workspace()` at line 365. The risk is that sub-agent calls or tool calls inside the PM loop that call `get_workspace()` again will get the updated global. Audit every call path from the PM loop that invokes `get_workspace()` and ensure all of them use the pre-captured `workspace` variable instead.

**Specific audit targets:**

- `app.py` line 365: `workspace = get_workspace()` — correct, this is captured at start.
- Verify `AgentFactory.get_agent()` and sub-agent `stream_response()` do NOT call `get_workspace()` internally. If they do, the `workspace` snapshot must be passed as a parameter.
- Verify `handle_save()` and `handle_pm_save()` use the passed `workspace` parameter, not `get_workspace()`.

**Full fix (per-session workspace):**

Replace the single `WORKSPACE_PATH` global with a session-keyed dictionary:

```python
# core/shared.py — replacement design (do not implement without D2 test results)
_session_workspaces: dict[str, str] = {}   # session_id -> workspace_path
_session_workspace_lock = threading.Lock()

def get_workspace(session_id: str | None = None) -> str:
    with _session_workspace_lock:
        if session_id and session_id in _session_workspaces:
            return _session_workspaces[session_id]
        return _DEFAULT_WORKSPACE

def set_workspace(path: str, session_id: str | None = None):
    with _session_workspace_lock:
        if session_id:
            _session_workspaces[session_id] = path
        else:
            # Backward-compatible: set default for all sessions without a session_id
            global WORKSPACE_PATH
            WORKSPACE_PATH = path
```

This full fix requires passing `session_id` through the entire call stack from `/api/chat` and `/api/workspace` down to every `get_workspace()` call.

### Acceptance Checklist

**Minimum viable fix:**
- [ ] Audit confirms no sub-agent or tool path inside the PM loop calls `get_workspace()` after the initial `workspace = get_workspace()` capture on line 365
- [ ] A comment in `core/shared.py` above `WORKSPACE_PATH` explicitly documents the global-state risk for multi-session deployments
- [ ] `WORKSPACE_PATH` risk is documented in `DEMO-READINESS-REPORT.md`

**Full fix (if scope allows):**
- [ ] `get_workspace()` and `set_workspace()` accept an optional `session_id` parameter
- [ ] `/api/chat` passes `session_id` from the request body to `get_workspace(session_id)`
- [ ] `/api/workspace POST` passes `session_id` to `set_workspace(path, session_id)`
- [ ] TC-2 from D2 passes after the full fix

### Definition of Done

```
DONE (minimum) when:
  Audit is complete and results documented
  No hidden get_workspace() calls exist inside the PM loop execution path
  Risk is documented in DEMO-READINESS-REPORT.md with a clear "single-user only" warning

DONE (full) when:
  Per-session workspace is implemented and TC-2 from D2 passes
  All sessions can hold different workspaces simultaneously without conflict

NOT DONE if:
  Audit was skipped and the code was assumed to be safe
  The global WORKSPACE_PATH risk is undocumented
```

### Fallback Plan

```
If per-session workspace implementation takes longer than 8 hours:
  Fallback: Ship with the minimum viable fix (audit + documentation)
            Add a prominent warning in the UI: "ระบบรองรับ 1 ผู้ใช้ต่อครั้ง"
            (System supports 1 user at a time)
  Trade-off: The system cannot be safely used by multiple people simultaneously
  Trigger: Implementation estimate exceeds 8 hours total
  Decision Owner: Project lead
```

### Scaling Consideration

```
Current: Single global workspace — only safe for 1 user
Bottleneck at: Any 2nd concurrent user who selects a different workspace
Mitigation: Full per-session workspace fix described above
Future-safe: No — this must be fixed before any multi-user deployment
```

---

## D4 — Rate Limiting on /api/chat

**Priority:** HIGH
**Estimated Effort:** 1–2 hours (High confidence)
**Execution Order:** Parallel with D1 — no dependency between them

### Evidence

File: `app.py`, lines 342–346

```python
@app.route('/api/chat', methods=['POST'])
def chat():
    if not request.json: return jsonify({'error': 'Invalid request'}), 400
    user_input = request.json.get('message', '').strip()
    if not user_input: return jsonify({'error': 'ไม่มีข้อความ'}), 400
```

There is no rate limiting decorator, no IP-based throttle, no per-session call frequency check, and no global concurrency limit on `/api/chat`. A single client can send hundreds of requests per second, each triggering a streaming call to the OpenRouter API.

File: `requirements.txt` (full file) — `flask-limiter` is not present:

```
flask
flask-cors
openai
python-dotenv
mcp
watchdog
python-docx
openpyxl
weasyprint
markdown
ddgs
```

### Problem Description

Without rate limiting, the following scenarios are unprotected:

1. **Accidental loop:** A frontend bug or browser retry causes rapid repeated requests, exhausting the OpenRouter API key's credit balance in minutes.
2. **Malicious abuse:** If the demo URL is accessible on a shared network, any user can send requests that bill against the shared API key.
3. **Resource exhaustion:** Many concurrent SSE connections hold gunicorn greenlets open for 30–90 seconds each. Unbounded request volume can exhaust the greenlet pool.

### Fix — Required Changes

**Step 1: Add flask-limiter to requirements.txt**

```
flask-limiter
```

**Step 2: Initialize the limiter in app.py after the Flask app is created**

Add after line 334 (`db.init_db()`):

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],             # no global limit; apply per-route
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)
```

**Step 3: Apply rate limit to /api/chat**

Replace:
```python
@app.route('/api/chat', methods=['POST'])
def chat():
```

With:
```python
@app.route('/api/chat', methods=['POST'])
@limiter.limit(os.getenv("CHAT_RATE_LIMIT", "10 per minute"))
def chat():
```

**Step 4: Return a Thai-language error on rate limit breach**

Add a custom error handler after the limiter initialization:

```python
from flask_limiter.errors import RateLimitExceeded

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    return jsonify({'error': 'คุณส่งคำสั่งบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่'}), 429
```

**Step 5: Add CHAT_RATE_LIMIT to .env.example**

```
# Rate limit for /api/chat (flask-limiter syntax: "10 per minute", "5 per second")
CHAT_RATE_LIMIT=10 per minute
```

**Note on storage_uri:** The default `memory://` storage works for a single gunicorn worker. With `GUNICORN_WORKERS=2` (from D1), rate limit counters are not shared across workers — each worker tracks its own counter. For a 2-worker setup, the effective limit is `2 x CHAT_RATE_LIMIT`. This is acceptable for a POC. If shared enforcement is required, set `RATELIMIT_STORAGE_URI=redis://localhost:6379/0` and add `redis` to requirements.txt.

### Acceptance Checklist

- [ ] `flask-limiter` is in `requirements.txt`
- [ ] `/api/chat` has the `@limiter.limit(...)` decorator
- [ ] The rate limit value is configurable via `CHAT_RATE_LIMIT` env variable (not hardcoded)
- [ ] Sending 11 requests in under 60 seconds from one IP returns HTTP 429
- [ ] The HTTP 429 response body contains a Thai-language error message
- [ ] `/api/health` and other routes are NOT rate-limited
- [ ] `CHAT_RATE_LIMIT` and `RATELIMIT_STORAGE_URI` are documented in `.env.example`

### Definition of Done

```
DONE when:
  All checklist items above pass
  Manual test: 11 rapid POST requests to /api/chat → 10 succeed, 11th returns 429
               with JSON body {"error": "คุณส่งคำสั่งบ่อยเกินไป..."}
  CHAT_RATE_LIMIT is documented and defaults to a safe value

NOT DONE if:
  Rate limit is hardcoded in the decorator (not env-driven)
  The 429 error body is Flask's default HTML page (not JSON)
  /api/health is accidentally rate-limited
```

### Fallback Plan

```
If flask-limiter causes startup errors or import conflicts:
  Fallback: Implement rate limiting at the nginx reverse proxy layer
            (nginx: limit_req_zone / limit_req directives)
  Trade-off: Requires nginx to be in the deployment stack; not applicable to direct Flask access
  Trigger: flask-limiter raises ImportError or breaks an existing route on startup
  Decision Owner: Backend developer
```

### Scaling Consideration

```
Current: memory:// storage — rate limits are per-worker, not globally shared
Bottleneck at: 2 workers = effective limit is 2x the configured value
Mitigation: Set RATELIMIT_STORAGE_URI=redis://... for shared enforcement across workers
Future-safe: Yes — storage_uri is configurable; upgrading to Redis requires only an env change
```

---

## D5 — Environment and Secrets Checklist for Production

**Priority:** HIGH
**Estimated Effort:** 1 hour (High confidence)
**Execution Order:** Parallel with D1 and D4

### Evidence

File: `.env.example`, lines 22–24 (malformed line detected)

```
# OpenRouter API request timeout in seconds (default: 60)
# เพิ่มถ้าใช้ model ที่ช้า หรือสร้างเอกสารยาวมาก
OPENROUTER_TIMEOUT=60/home/user/ai-poc,/mnt/shared
ALLOWED_WORKSPACE_ROOTS=
```

Line 23 has `OPENROUTER_TIMEOUT=60/home/user/ai-poc,/mnt/shared` which is a corruption — the example value for `ALLOWED_WORKSPACE_ROOTS` was accidentally appended to `OPENROUTER_TIMEOUT`. Any developer who copies `.env.example` to `.env` without editing this line will have `OPENROUTER_TIMEOUT` set to an invalid value. `core/shared.py` lines 43–46 handle this:

```python
try:
    _TIMEOUT = float(os.getenv('OPENROUTER_TIMEOUT', '60'))
except ValueError:
    _logging.getLogger(__name__).warning("[shared] Invalid OPENROUTER_TIMEOUT value, defaulting to 60.0")
    _TIMEOUT = 60.0
```

The code gracefully falls back to 60.0 seconds, but the warning is silent unless the developer watches logs. The malformed `.env.example` is a reliability and developer experience bug.

File: `core/shared.py`, lines 9–16

```python
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
...
if not OPENROUTER_API_KEY:
    _logging.getLogger(__name__).error(
        "[shared] OPENROUTER_API_KEY is not set — copy .env.example to .env and set your key."
    )
```

The application starts without an API key and only logs an error. The first actual API call will fail with an authentication error, not a startup failure. A missing key is not caught at startup — it is a silent failure that surfaces only when a user sends a message.

File: `requirements.txt` — missing production dependencies identified in D1 and D4:
- `gunicorn` — not present
- `gevent` — not present
- `flask-limiter` — not present

### Fix — Required Changes

**Step 1: Fix the malformed line in `.env.example`**

Replace the malformed lines 22–24 with:

```
# OpenRouter API request timeout in seconds (default: 60)
# เพิ่มถ้าใช้ model ที่ช้า หรือสร้างเอกสารยาวมาก
OPENROUTER_TIMEOUT=60

# Allowed workspace roots — comma-separated absolute paths
# User can only pick/create workspaces under these directories (runtime safety)
# ถ้าไม่กำหนด จะใช้ project root เป็น default
# Example: ALLOWED_WORKSPACE_ROOTS=/home/user/ai-poc,/mnt/shared
ALLOWED_WORKSPACE_ROOTS=
```

**Step 2: Add gunicorn config variables to `.env.example`** (from D1)

```
# Gunicorn server config (production)
GUNICORN_WORKERS=2
GUNICORN_CONNECTIONS=50
GUNICORN_TIMEOUT=120
GUNICORN_LOG_LEVEL=info
```

**Step 3: Add rate limit config to `.env.example`** (from D4)

```
# Rate limiting for /api/chat
CHAT_RATE_LIMIT=10 per minute
RATELIMIT_STORAGE_URI=memory://
```

**Step 4: Add a startup validation check in app.py**

Add after line 29 (`logger = logging.getLogger(__name__)`):

```python
# Startup validation — fail fast if critical config is missing
if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set. "
        "Copy .env.example to .env and set your key before starting the server."
    )
```

This converts a silent runtime failure into a hard startup failure. Operations staff will know immediately why the server did not start.

### Production .env Checklist

Before any deployment, verify each of the following:

| Variable | Required | Safe Default | Notes |
|----------|----------|-------------|-------|
| `OPENROUTER_API_KEY` | YES | none | Must be a valid `sk-or-v1-...` key |
| `OPENROUTER_MODEL` | No | `anthropic/claude-sonnet-4-5` | Change to cheaper model for cost control |
| `OPENROUTER_TIMEOUT` | No | `60` | Increase to `120` for PM mode |
| `WORKSPACE_PATH` | No | `./workspace` | Use absolute path in production |
| `ALLOWED_WORKSPACE_ROOTS` | No | project root | Set to restrict filesystem access |
| `FLASK_DEBUG` | No | (unset = False) | MUST be unset or `false` in production |
| `FLASK_HOST` | No | `0.0.0.0` | Use `127.0.0.1` if behind nginx |
| `MAX_PENDING_DOC_BYTES` | No | `204800` (200KB) | Increase only if large documents are needed |
| `GUNICORN_WORKERS` | No | `2` | Set to number of CPU cores |
| `GUNICORN_CONNECTIONS` | No | `50` | Greenlets per worker |
| `GUNICORN_TIMEOUT` | No | `120` | Must be > OPENROUTER_TIMEOUT |
| `CHAT_RATE_LIMIT` | No | `10 per minute` | Adjust for expected usage |
| `RATELIMIT_STORAGE_URI` | No | `memory://` | Use `redis://` for multi-worker enforcement |

### Security Items Checklist

- [ ] `.env` is in `.gitignore` (already confirmed in `.env.example` comment line 3)
- [ ] `FLASK_DEBUG` is not set to `1` or `true` in the production `.env`
- [ ] `OPENROUTER_API_KEY` has a usage budget set on the OpenRouter dashboard
- [ ] `ALLOWED_WORKSPACE_ROOTS` is set to restrict filesystem access to known safe paths
- [ ] The deployment machine does not have the `.env` file world-readable (`chmod 600 .env`)
- [ ] The server is not exposed directly on port 5000 to the public internet (put nginx in front)

### Acceptance Checklist

- [ ] `.env.example` has no malformed lines — `OPENROUTER_TIMEOUT` and `ALLOWED_WORKSPACE_ROOTS` are on separate lines
- [ ] All variables from D1 and D4 are documented in `.env.example`
- [ ] `app.py` raises `RuntimeError` at startup if `OPENROUTER_API_KEY` is not set
- [ ] Starting the server without a `.env` file produces an immediate, actionable error message
- [ ] The production `.env` checklist table above is reviewed and signed off before deployment

### Definition of Done

```
DONE when:
  .env.example is corrected and all new variables from D1/D4 are added
  Starting gunicorn without OPENROUTER_API_KEY raises RuntimeError with a clear message
  The production .env checklist is reviewed and all "Required: YES" rows are confirmed

NOT DONE if:
  .env.example still has the malformed OPENROUTER_TIMEOUT line
  The server starts silently with a missing API key (no startup error)
  FLASK_DEBUG is set to 1 in the production environment
```

### Fallback Plan

```
If adding the RuntimeError startup check breaks an automated test harness that
starts the app without a real API key (e.g., smoke_test_phase0.py with mocked keys):
  Fallback: Check for a TEST_MODE env variable and skip the RuntimeError in test mode
            if TEST_MODE=1, log a warning instead of raising
  Trade-off: Test mode must be explicitly set — slightly more test setup required
  Trigger: CI or smoke tests fail to start the app after the RuntimeError is added
  Decision Owner: Backend developer
```

### Scaling Consideration

```
Current: .env file on a single machine — adequate for POC
Bottleneck at: Any multi-instance deployment where .env must be synchronized
Mitigation: Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, or
            environment injection via systemd EnvironmentFile) instead of .env files
Future-safe: No — .env files do not scale to multi-instance deployments.
             This is acceptable for the POC. Document as a known limitation.
```

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|-----------|--------|------------|-------|
| R1 | gevent incompatible with watchdog or weasyprint, causing gunicorn startup failure | Medium | High | Test startup immediately after D1; fallback to gthread (documented in D1) | Backend developer |
| R2 | OpenRouter rate limit hit during D2 concurrency testing (3 simultaneous PM requests) | High | Medium | Use cheaper/faster model during tests; space out test runs | Backend developer |
| R3 | Workspace contamination discovered in D2 testing causes document data loss in existing demo data | Medium | High | Back up workspace/ and temp/ before running D2 tests | Backend developer |
| R4 | flask-limiter breaks existing routes (unintended rate limiting) | Low | High | Apply limiter only to /api/chat; test all other routes after D4 implementation | Backend developer |
| R5 | .env.example malformed line has already been copied to production .env by a developer | Medium | Medium | Check production .env for the malformed OPENROUTER_TIMEOUT value before deployment | Project lead |
| R6 | Startup RuntimeError (D5) breaks smoke_test_phase0.py in CI | Medium | Low | Add TEST_MODE fallback as described in D5 fallback plan | Backend developer |

**Risk Classification:**
- R1: High x High — verify D1 immediately; do not proceed to D2 until resolved
- R2: High x Medium — monitor OpenRouter usage dashboard during D2; pause if credits drop unexpectedly
- R3: Medium x High — backup required before D2 starts
- R4: Low x High — full route test required after D4
- R5: Medium x Medium — check production .env as part of D5 checklist
- R6: Medium x Low — accept and implement fallback if it occurs

---

## Fallback Strategy Map

```
Primary Plan
    |
    +-- D1 (gunicorn + gevent) fails to start
    |       --> Try gthread worker class (see D1 Fallback)
    |       --> If gthread also fails, debug import conflicts before proceeding
    |
    +-- D2 (concurrency test) reveals workspace corruption
    |       --> Immediate: add per-request workspace snapshot guard (see D2 Fallback)
    |       --> Full fix: implement per-session workspace (see D3 Full Fix)
    |       --> Must-have before deployment: document single-user limitation in UI
    |
    +-- D3 (per-session workspace) exceeds 8 hours
    |       --> Ship minimum viable fix: audit + documentation + UI warning
    |       --> Defer full per-session implementation to v0.18.0
    |
    +-- D4 (flask-limiter) causes startup error
    |       --> Switch to nginx rate limiting (see D4 Fallback)
    |       --> If no nginx: implement manual request counter in app.py using threading.Semaphore
    |
    +-- D5 (startup RuntimeError) breaks tests
            --> Add TEST_MODE=1 bypass (see D5 Fallback)
            --> Ensure TEST_MODE=1 is never set in production .env
```

---

## Timeline View

```
Day 1                    Day 2                    Day 3
+----------------------++----------------------++----------------------+
| D1: gunicorn setup   || D2: concurrency tests|| D3: workspace audit  |
| D4: rate limiting    || (requires D1 done)   || D3: full fix if time |
| D5: .env fixes       ||                      ||                      |
| .env.example repair  || Review D2 results    || Final smoke test     |
| requirements.txt     || Fix any issues found || Deploy               |
+----------------------++----------------------++----------------------+
       |                          |                        |
  [D1+D4+D5 done]          [D2 results known]      [All DoDs met]
  [can run D2]             [D3 scope decided]       [DEPLOY]
```

---

## Assumptions and Open Questions

**Assumptions Made:**

1. The deployment target is the same WSL machine (single instance, not a cloud multi-instance setup). *If wrong: D3 full per-session workspace fix becomes CRITICAL, and D4 rate limit storage must be Redis.*

2. The OpenRouter API key used for production has a budget cap configured on the OpenRouter dashboard. *If wrong: an accidental PM loop flood can exhaust the credit balance before rate limiting (D4) kicks in.*

3. Python 3.8+ is available (gevent and flask-limiter both require it). *If wrong: check Python version with `python3 --version` and upgrade if needed.*

4. The demo audience is a small group (< 5 simultaneous users). *If wrong: the gunicorn worker count in D1 and the rate limit in D4 must be recalculated.*

**Open Questions (must resolve before deployment):**

- Is the deployment machine exposed on a network accessible to people outside the demo team? If yes, D4 (rate limiting) must be implemented before D1 (starting gunicorn makes the server more robust and thus more likely to be left running).
- Is there a CI pipeline that runs `smoke_test_phase0.py` automatically? If yes, confirm how it sets `OPENROUTER_API_KEY` before the D5 startup validation is added.
- Does the demo require multiple users to work in separate workspaces simultaneously? If yes, D3 full fix must be treated as CRITICAL and moved to Day 1.

---

## Handoff Notes

**Backend developer executing D1 and D2:**

The Flask app already has `from core.shared import ... get_workspace, set_workspace`. The gevent monkey-patching required for gunicorn must happen before any other imports. Add this as the very first two lines of `app.py` (before any other imports) if startup issues occur with watchdog:

```python
from gevent import monkey
monkey.patch_all()
```

This is a common requirement when mixing gevent with libraries that use Python's standard `threading` or `socket` modules. `watchdog` uses threading internally. The `_workspace_lock` and `_ws_change_lock` in `core/shared.py` are `threading.Lock()` instances that gevent will patch to cooperative locks if `monkey.patch_all()` is called.

**Backend developer executing D4:**

The limiter's `key_func=get_remote_address` uses the `X-Forwarded-For` header if present. If the app is behind nginx, ensure nginx sets `X-Real-IP` and `X-Forwarded-For` correctly, or an attacker behind a proxy can spoof their IP and bypass the rate limit. For the POC/demo without nginx, `get_remote_address` is safe.

**Anyone executing D5 (.env fix):**

The malformed line in `.env.example` is on line 23: `OPENROUTER_TIMEOUT=60/home/user/ai-poc,/mnt/shared`. This is the only corrupted line. The fix is a one-line edit. Verify no developer has already copied this to a production `.env` before the fix is deployed.

**Reviewer before deployment:**

Run the full sequence: D1 (gunicorn starts) → D5 (no malformed env) → D4 (rate limit test) → D2 (concurrency test) → D3 audit. Each step's Definition of Done must be checked by someone other than the implementer. Do not deploy until the project-level Definition of Done below is met.

---

## Project-Level Definition of Done

```
DONE when:
  D1: gunicorn + gevent is running and confirmed with: ps aux | grep gunicorn
  D1: Two concurrent SSE streams both receive tokens simultaneously
  D2: All four test cases pass and results are documented
  D3: Workspace audit is complete; risk is documented or full fix is implemented
  D4: /api/chat returns 429 after 10 requests/minute from one IP
  D5: .env.example has no malformed lines; all new variables are documented
  D5: Server refuses to start without OPENROUTER_API_KEY (RuntimeError)
  smoke_test_phase0.py passes on the gunicorn server (not the dev server)
  DEMO-READINESS-REPORT.md is updated to reflect all changes

NOT DONE if:
  start.sh still calls python app.py
  Any D-level item has an open checklist box
  Deployment was tested only in the dev server environment
  FLASK_DEBUG=1 is present in the production .env
  The workspace global state risk is undocumented
```
