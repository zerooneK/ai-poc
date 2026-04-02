# Developer Guide — AI Assistant Internal POC

> **Version:** v0.31.0 | **Last updated:** 2026-04-02
>
> This guide is for developers who want to understand the codebase in depth, add new agents or
> tools, modify routing behaviour, or write tests. It assumes you have already followed the setup
> instructions in `README.md` and the architecture overview in `docs/ARCHITECTURE.md`.

---

## Table of Contents

1. [Development Environment Setup](#1-development-environment-setup)
2. [Project Conventions](#2-project-conventions)
3. [How to Add a New Agent](#3-how-to-add-a-new-agent)
4. [How to Add a New Tool](#4-how-to-add-a-new-tool)
5. [How to Add a New API Endpoint](#5-how-to-add-a-new-api-endpoint)
6. [How to Modify the Orchestrator Routing](#6-how-to-modify-the-orchestrator-routing)
7. [SSE Event Handling](#7-sse-event-handling)
8. [Working with the Database](#8-working-with-the-database)
9. [Testing](#9-testing)
10. [Debugging](#10-debugging)
11. [Code Review Checklist](#11-code-review-checklist)
12. [Version Bumping and Commit Format](#12-version-bumping-and-commit-format)
13. [Common Pitfalls](#13-common-pitfalls)

---

## 1. Development Environment Setup

### Prerequisites

- Python 3.12, `git`, `make` (optional)
- WSL2 on Windows, or a native Linux/macOS environment
- A valid `OPENROUTER_API_KEY` in your `.env`

### First-time setup

```bash
git clone <repo-url>
cd ai-poc
bash setup.sh           # installs system libs, creates venv, copies .env.example
nano .env               # set OPENROUTER_API_KEY
./start.sh              # starts Flask on :5000 (and Next.js on :3000 if frontend/ exists)
```

### Running only the Flask backend (no Next.js)

```bash
source venv/bin/activate
./venv/bin/gunicorn --config gunicorn.conf.py "app:app"
```

Or for quick iteration with the Flask dev server (auto-reload on code changes):

```bash
FLASK_DEBUG=1 ./venv/bin/python3 app.py
```

**Do not use `FLASK_DEBUG=1` in production.** It disables Gunicorn and runs Flask's single-threaded dev server, which cannot handle concurrent SSE connections.

### Useful environment flags during development

```bash
# More verbose logging from the app
GUNICORN_LOG_LEVEL=debug ./venv/bin/gunicorn --config gunicorn.conf.py "app:app"

# Faster web search timeout (skip slow searches in dev)
WEB_SEARCH_TIMEOUT=5 ./start.sh

# Use a cheaper/faster model for testing
OPENROUTER_MODEL=openai/gpt-4o-mini ./start.sh
```

---

## 2. Project Conventions

### File naming

All Python files: `snake_case.py`. All Markdown prompt files: `snake_case.md`. No Thai characters in filenames — only `english_snake_case.ext`.

### Python style

- The project does not enforce a linter. Follow existing code style: 4-space indentation, 120-char soft line limit.
- All user-facing strings and all AI prompt text are in Thai.
- All code comments, docstrings, and log messages are in English.
- All module-level constants are `UPPER_SNAKE_CASE`.
- Private helpers are prefixed with `_`.

### Logging

Use the module-level logger everywhere:

```python
import logging
logger = logging.getLogger(__name__)
```

Log levels:
- `DEBUG` — verbose tracing, tool argument dumps
- `INFO` — normal operational events (file saved, agent selected)
- `WARNING` — recoverable errors, unexpected-but-handled situations (fake tool call stripped, empty LLM response)
- `ERROR` — exceptions that were caught but represent failures (save failed, DB write failed)

Never use `print()` in production code. Use `logger`.

### Error handling

Catch the most specific exception possible. The general pattern in this codebase:

```python
try:
    # operation that may fail
except (SpecificError, AnotherSpecificError) as e:
    logger.warning("[context] description: %s", e)
    return safe_default
except Exception as e:
    logger.error("[context] unexpected error: %s", e, exc_info=True)
    raise   # or return safe_default depending on context
```

Never swallow `Exception` silently (without logging). Always include `exc_info=True` on `logger.error` calls for unexpected exceptions.

### SSE event format

All events yielded from `run_with_tools()` are raw dicts. `app.py` calls `format_sse()` before yielding to the HTTP response. Do not call `format_sse()` inside agent code.

```python
# Correct — agent yields a dict
yield {"type": "text", "content": chunk}

# Wrong — agent should not format SSE
yield format_sse({"type": "text", "content": chunk})
```

---

## 3. How to Add a New Agent

Follow these steps to add a new domain agent (e.g., a `LegalAgent`).

### Step 1: Write the system prompt

Create `prompts/legal_agent.md`. Follow the established structure shared by all agents:

```markdown
คุณคือ Legal Agent ผู้เชี่ยวชาญด้านกฎหมายสำหรับองค์กรไทย
...

สไตล์การตอบ:
- เริ่มด้วยการ acknowledge งานสั้นๆ 1 ประโยคก่อน output เอกสาร

การใช้ list_files และ read_file:
- ใช้เฉพาะเมื่อผู้ใช้ขอแก้ไขหรืออ้างอิงเอกสารที่มีอยู่แล้วโดยตรง

การใช้ web_search:
- ค้นหาได้สูงสุด 2 ครั้งเท่านั้น ด้วย query ที่แตกต่างกัน

กฎการเรียกใช้ tools (สำคัญมาก):
- ห้ามเขียน JSON ของ tool call เป็น plain text เด็ดขาด

สำคัญ: ระบุที่ท้ายเอกสารทุกครั้งว่า
"⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"

หลังแสดงเอกสารแล้ว:
- ถ้าคำสั่งขึ้นต้นด้วย "[PM_SUBTASK]" ให้จบที่บรรทัด ⚠️ disclaimer เท่านั้น
- ถ้าไม่มี "[PM_SUBTASK]" ให้ลงท้ายด้วย: "💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์"
```

Include the acknowledgement style, tool usage policy, anti-fake-tool-call rule, AI disclaimer, and PM_SUBTASK footer rule. These are mandatory for consistency.

### Step 2: Create the agent class

Create `agents/legal_agent.py`:

```python
from agents.base_agent import BaseAgent
from core.utils import load_prompt

class LegalAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Legal Agent", system_prompt=load_prompt("legal_agent"))
```

That is all that is needed for a standard domain agent. The name string appears in status messages in the UI.

### Step 3: Register in AgentFactory

Edit `core/agent_factory.py`. Add the import at the top:

```python
from agents.legal_agent import LegalAgent
```

Add the case inside `get_agent()`:

```python
elif agent_type == 'legal':
    cls._agents[agent_type] = LegalAgent()
```

### Step 4: Update the Orchestrator routing rules

Edit `prompts/orchestrator.md`. Add the new key to the JSON output examples:

```
{"agent": "legal", "reason": "เหตุผลสั้นๆ"}
```

Add a routing description section:

```
Legal Agent เหมาะกับ:
- สัญญาทางธุรกิจ (NDA, ข้อตกลง, MOU)
- คำปรึกษากฎหมายแรงงาน
- การวิเคราะห์ความเสี่ยงทางกฎหมาย
```

### Step 5: Update `docs/AGENTS.md`

Add a section for the new agent following the established format (use cases, document style, tool usage policy).

### Step 6: Update `README.md`

Add the new agent to the Agent Overview table and the Chat Agent's system prompt (so Chat knows about it).

### Step 7: Test

```bash
# Start the server
./start.sh

# Send a request that should route to the new agent
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "ร่าง NDA ระหว่างบริษัท ABC และ XYZ", "session_id": "dev-test-12345678"}'
```

Watch the SSE stream. The `agent` event should show `"agent": "legal"`.

---

## 4. How to Add a New Tool

Tools are defined in `app.py` as OpenAI function calling schema objects, implemented in `core/utils.py` via `execute_tool()`, and presented to agents via the `tools` parameter in `run_with_tools()`.

### Step 1: Implement the tool function in `core/utils.py`

Add a new branch inside `execute_tool()`:

```python
elif tool_name == 'summarize_file':
    filename = tool_args.get('filename', '')
    # ... implementation ...
    return result_string
```

The function must:
- Accept `workspace: str` and `tool_args: dict`
- Return a plain string (success message or content)
- Return a string starting with `❌` on failure (this is how `_tool_result_is_error()` detects failures)
- Raise no exceptions that are not already caught by the outer `try/except` in `execute_tool()`

### Step 2: Define the tool schema in `app.py`

Add a new dict to the `MCP_TOOLS` list:

```python
{
    "type": "function",
    "function": {
        "name": "summarize_file",
        "description": "สรุปเนื้อหาของไฟล์ใน workspace ให้กระชับ",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "ชื่อไฟล์ที่ต้องการสรุป"
                }
            },
            "required": ["filename"]
        }
    }
}
```

### Step 3: Add it to the appropriate tool set

Decide which tool set gets the new tool:

- `READ_ONLY_TOOLS` — for tools that only read or have no side effects
- `MCP_TOOLS` (full set) — if the tool is a write operation (not currently offered to agents)
- `LOCAL_AGENT_TOOLS` — for tools that apply in local agent mode only

```python
READ_ONLY_TOOLS = [t for t in MCP_TOOLS if t['function']['name'] in (
    'list_files', 'read_file', 'web_search', 'request_delete', 'summarize_file'  # added
)]
```

### Step 4: Add a status message in `BaseAgent.run_with_tools()`

In `agents/base_agent.py`, add an `elif` branch inside the tool call status section so the UI shows a meaningful progress indicator:

```python
elif tool_name == 'summarize_file':
    yield {"type": "status", "message": f"{self.name} กำลังสรุปไฟล์..."}
```

### Step 5: Update the agent prompts

Add instructions in the affected agent prompt files explaining when to use the new tool. Follow the existing pattern for `list_files` and `read_file`:

```markdown
การใช้ summarize_file:
- ใช้เมื่อผู้ใช้ขอสรุปเนื้อหาของไฟล์ที่มีอยู่แล้ว
- ใช้เฉพาะเมื่อผู้ใช้ระบุชื่อไฟล์ชัดเจน
```

### Step 6: Update `docs/AGENTS.md`

Add the new tool to the Tool Reference section.

---

## 5. How to Add a New API Endpoint

### Step 1: Implement the route in `app.py`

Add the route function after the existing routes, using the established patterns:

```python
@app.route('/api/my_endpoint', methods=['POST'])
def my_endpoint():
    # 1. Validate session ID if workspace-sensitive
    if _has_invalid_request_session_id():
        return jsonify({'error': 'invalid session_id'}), 400

    # 2. Parse and validate input
    data = request.json or {}
    my_param = (data.get('my_param') or '').strip()
    if not my_param or not re.match(r'^[\w.\-]{1,120}$', my_param):
        return jsonify({'error': 'invalid my_param'}), 400

    # 3. Resolve workspace
    session_id = _get_request_session_id()
    workspace = get_session_workspace(session_id) if session_id else get_workspace()

    # 4. Do work
    result = some_operation(workspace, my_param)

    # 5. Return JSON response
    return jsonify({'result': result}), 200
```

**Rules:**
- Always validate `session_id` before using it for workspace resolution.
- Validate all file-related parameters with `re.match(r'^[\w.\-]{1,120}$', ...)`.
- Never call `get_workspace()` twice — capture it once and pass it through.
- Return HTTP 400 for client errors, 500 only for unexpected server errors.

### Step 2: Add rate limiting if needed

```python
@app.route('/api/my_endpoint', methods=['POST'])
@limiter.limit("5 per minute")
def my_endpoint():
    ...
```

### Step 3: Document the endpoint in `docs/API_REFERENCE.md`

Follow the established template: method, path, description, request fields table, response shape, error codes, example cURL command.

---

## 6. How to Modify the Orchestrator Routing

All routing rules live in `prompts/orchestrator.md`. The Orchestrator is prompt-only — there is no routing logic in Python code. To change routing:

1. Edit `prompts/orchestrator.md` — add, modify, or remove agent key descriptions.
2. Restart the server (prompt files are loaded at agent instantiation time, which happens on first request if using the lazy factory, or at startup if agents are pre-warmed).
3. Test with representative messages for all affected domains.

**If you add a new agent key**, you must also:
- Handle it in `AgentFactory.get_agent()` (see [Section 3](#3-how-to-add-a-new-agent))
- Add it to the valid JSON examples in `prompts/orchestrator.md`

**The fallback:** if the Orchestrator returns an unrecognised agent key, `AgentFactory` logs a warning and falls back to `ChatAgent`. This means routing failures are not fatal — the chat continues.

**To test routing without a UI:**

```bash
# Quick routing test via curl
curl -s -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "ออก Invoice", "session_id": "routing-test-00000001"}' \
  | grep -o '"agent":"[^"]*"' | head -1
# Expected: "agent":"accounting"
```

---

## 7. SSE Event Handling

### Adding a new SSE event type

1. In `agents/base_agent.py`, yield the new event dict from `run_with_tools()`:
   ```python
   yield {"type": "my_event", "data": "some value"}
   ```

2. In `app.py` inside `generate()`, the event will automatically be formatted and forwarded to the browser via `format_sse(sse_data)`. If the new event needs special handling before forwarding (like the `local_delete` intercept), add it in the interception block:
   ```python
   elif (sse_data.get('type') == 'my_event'):
       # transform or handle
       yield format_sse({'type': 'my_event', 'processed': True})
   else:
       yield format_sse(sse_data)
   ```

3. In `index.html`, handle the new event type in the `EventSource.onmessage` handler:
   ```javascript
   case 'my_event':
       handleMyEvent(data);
       break;
   ```

4. Document the new event in `docs/API_REFERENCE.md` under the SSE Event Schema Reference section and in `docs/ARCHITECTURE.md` under the SSE Event Types table.

### `format_sse()` contract

`format_sse(data: dict) -> str` serialises a dict to `data: <json>\n\n`. It uses `ensure_ascii=False` so Thai characters are not escaped.

```python
from core.utils import format_sse

# Returns: 'data: {"type": "text", "content": "สวัสดี"}\n\n'
format_sse({"type": "text", "content": "สวัสดี"})
```

---

## 8. Working with the Database

### Schema

Two tables — `jobs` and `saved_files`. See `docs/ARCHITECTURE.md` Section 10 for the ER diagram.

### All public functions

```python
import db

db.init_db()                                        # call once at startup
job_id = db.create_job(user_input, session_id)     # returns str UUID or None
db.update_job_agent(job_id, agent, reason)
db.complete_job(job_id, output_text)
db.fail_job(job_id)
db.discard_job(job_id)
db.record_file(job_id, filename, agent, size_bytes)

jobs = db.get_history(limit=50)                    # list of dicts
job  = db.get_job(job_id)                          # dict or None
sessions = db.get_sessions(limit=20)               # list of dicts
jobs = db.get_session_jobs(session_id)             # list of dicts
deleted = db.delete_session(session_id)            # bool
status = db.db_status()                            # {"available": bool, "path": str}
```

### Thread safety

All writes go through `_db_write_lock = threading.Lock()`. Reads use a fresh connection per call (`_connect()` opens a new `sqlite3.Connection`). The WAL journal mode means reads do not block writes.

### Adding a new column

1. Add the column with a default value (so existing rows are compatible):
   ```sql
   ALTER TABLE jobs ADD COLUMN my_column TEXT DEFAULT '';
   ```
   Add this inside `init_db()` using `conn.executescript()`. Wrap it in a `try/except` so it is idempotent:
   ```python
   try:
       conn.execute("ALTER TABLE jobs ADD COLUMN my_column TEXT DEFAULT ''")
   except sqlite3.OperationalError:
       pass  # Column already exists
   ```

2. Update `get_history()`, `get_job()`, and any other read functions to include the new column.

3. Update `create_job()` or whichever write function should populate it.

**Never use destructive migrations** (DROP TABLE, DROP COLUMN) in `init_db()` — it runs at startup on production with live data.

---

## 9. Testing

### Test files in the project root

| File | Purpose | Requires server |
|---|---|---|
| `smoke_test_phase0.py` | Environment checks: venv, dependencies, workspace dirs, .env format | No |
| `test_cases.py` | End-to-end agent flow tests: sends requests, checks SSE event sequence | Yes — `http://localhost:5000` |
| `test_concurrency_pm.py` | Concurrency tests for PM Agent multi-subtask flows | Yes |
| `quick-demo-check.py` | Fast readiness check before demos | Yes |

### Running tests

```bash
# Phase 0 smoke tests (no server needed, no API calls)
./venv/bin/python3 smoke_test_phase0.py

# End-to-end tests (requires running server + valid API key)
PYTHONUTF8=1 ./venv/bin/python3 test_cases.py

# Specific concurrency test cases
./venv/bin/python3 test_concurrency_pm.py --tc 1 2 3
```

### Writing a new test case in `test_cases.py`

Follow the existing pattern:

```python
def test_my_new_feature():
    """Test description in English."""
    resp = requests.post(BASE_URL + "/api/chat", json={
        "message": "your test message",
        "session_id": f"test-{uuid.uuid4().hex[:16]}"
    }, stream=True, timeout=60)

    events = collect_sse_events(resp)   # helper that parses the SSE stream

    # Check that the agent event has the expected key
    agent_events = [e for e in events if e.get('type') == 'agent']
    assert agent_events, "No agent event received"
    assert agent_events[0]['agent'] == 'hr', f"Expected hr, got {agent_events[0]['agent']}"

    # Check that done was received
    done_events = [e for e in events if e.get('type') == 'done']
    assert done_events, "Stream did not complete with done event"

    print("PASS: test_my_new_feature")
```

### Manual testing via curl

```bash
# Test a document request and see all SSE events
curl -s -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "ทำสัญญาจ้างงาน", "session_id": "manual-test-12345678"}' \
  | while IFS= read -r line; do echo "$line"; done

# Test save confirmation
curl -s -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "บันทึก",
    "session_id": "manual-test-12345678",
    "pending_doc": "# สัญญา\n\nเนื้อหา...",
    "pending_agent": "hr"
  }'
```

---

## 10. Debugging

### Enable Flask debug mode (dev server only)

```bash
FLASK_DEBUG=1 ./venv/bin/python3 app.py
```

The Flask dev server auto-reloads on file changes, shows full tracebacks in the browser, and enables the Werkzeug interactive debugger.

### Verbose Gunicorn logging

```bash
GUNICORN_LOG_LEVEL=debug ./venv/bin/gunicorn --config gunicorn.conf.py "app:app"
```

### Tracing SSE events

Add temporary `print` statements in `generate()` or use the existing `logger.info` calls. Each SSE event is logged at `DEBUG` level.

To inspect raw SSE output from the terminal:

```bash
curl -s -N -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "debug-00000001"}'
```

### Inspecting agent tool calls

In `agents/base_agent.py`, the tool call accumulation loop logs at `WARNING` level when fake tool calls are stripped. To see all tool invocations, add a temporary `logger.debug` in the tool execution block:

```python
logger.debug("[%s] executing tool %s with args %s", self.name, tool_name, args)
```

### Testing a prompt change without restarting

Prompt files (`prompts/*.md`) are read by `load_prompt()` at agent instantiation time. Because agents are cached as singletons by `AgentFactory`, a prompt change does not take effect until you either:
- Restart the server, or
- Bypass the cache temporarily (not recommended in production)

For rapid prompt iteration:

```bash
# Make your change to prompts/hr_agent.md, then:
sudo systemctl restart ai-poc   # or kill and restart gunicorn in dev
```

### Inspecting the SQLite database

```bash
./venv/bin/python3 -c "
import db
db.init_db()
jobs = db.get_history(10)
for j in jobs:
    print(j['created_at'], j['agent'], j['status'], j['user_input'][:50])
"
```

Or directly:

```bash
sqlite3 data/assistant.db
.tables
SELECT id, agent, status, substr(user_input,1,40) FROM jobs ORDER BY created_at DESC LIMIT 5;
.quit
```

### Common error messages and their causes

| Log message | Cause | Fix |
|---|---|---|
| `❌ ไม่พบไฟล์ prompt: 'prompts/X.md'` | `load_prompt('X')` called but `prompts/X.md` does not exist | Create the file or fix the agent class constructor |
| `[AgentFactory] Unknown agent_type 'X'` | Orchestrator returned an unrecognised key | Add the key to `AgentFactory.get_agent()` or fix the orchestrator prompt |
| `[db] Unavailable` at startup | SQLite file not writable or `data/` directory missing | `mkdir -p data && chmod 755 data` |
| `[web_search] error: timeout` | `WEB_SEARCH_TIMEOUT` too short, or DuckDuckGo blocked | Increase `WEB_SEARCH_TIMEOUT` or test network connectivity |
| `finish_reason=length` | LLM hit max_tokens mid-response | Increase `AGENT_MAX_TOKENS` in `.env` |
| `ValueError: ไม่อนุญาต: ... อยู่นอก workspace` | Path traversal attempt in tool args | Check filename sanitisation; this is the MCP sandbox blocking an escape attempt |

---

## 11. Code Review Checklist

The project uses Claude Code subagents defined in `.claude/agents/` for automated review. Before committing, run:

| Change type | Subagent to run |
|---|---|
| `app.py`, `core/`, `agents/`, `db.py`, `converter.py`, `mcp_server.py` | `backend-python-reviewer` (mandatory — block commit on failure) |
| Other `.py` files (test scripts, utilities) | `python-reviewer` |
| `index.html`, `history.html` | `ui-ux-reviewer` |
| `.env` changes, API config | `security-checker` |
| `db.py`, `converter.py` | `db-checker` |
| Thai-language files (`docs/`, `prompts/`, `CHANGELOG.md`, agent outputs) | `thai-doc-checker` (mandatory for Thai content) |

To invoke a subagent in Claude Code:

```
/backend-python-reviewer
/thai-doc-checker
```

### Manual checklist

Before every commit:
- [ ] No real API keys or secrets in any committed file
- [ ] All new filenames are `english_snake_case.ext` (no Thai characters)
- [ ] New environment variables have entries in `.env.example` with comments
- [ ] Version in `index.html` has been bumped
- [ ] New changelog entry added to `docs/CHANGELOG.md`
- [ ] All new Thai-language content has the AI draft disclaimer
- [ ] `FLASK_DEBUG=0` in `.env.example` (never commit with debug=1)
- [ ] No hardcoded workspace paths (use `get_workspace()` / `get_session_workspace()`)

---

## 12. Version Bumping and Commit Format

### Version location

The canonical version is the `.version-tag` span in `index.html`:

```html
<span class="version-tag">v0.31.0</span>
```

Bump this manually before committing. Use semantic versioning:
- **Patch** `v0.x.y → v0.x.(y+1)`: bug fixes, prompt tweaks, minor adjustments
- **Minor** `v0.x.y → v0.(x+1).0`: new agent, new tool, new endpoint, new UI feature
- **Major** `v1.0.0+`: breaking changes, database schema redesign, complete UI rewrite

### Changelog entry

Add to `docs/CHANGELOG.md` (see the existing format — newest entry at top):

```markdown
## v0.32.0 — 2026-04-15

### Added
- Legal Agent: handles NDA, MOU, and contract advisory requests

### Changed
- Orchestrator: added `legal` routing key

### Fixed
- Accounting Agent: VAT calculation now correctly rounds to 2 decimal places
```

### Commit message format

```
vX.X.X — [fix/feature/refactor/docs]: description in Thai or English

Examples:
v0.32.0 — feature: เพิ่ม Legal Agent สำหรับงานด้านกฎหมาย
v0.31.1 — fix: แก้ไข PM Agent ไม่ส่ง subtask_done event เมื่อ error
v0.31.2 — docs: อัปเดต ARCHITECTURE.md และ AGENTS.md
```

### Git workflow

```bash
# Stage only the files you changed
git add app.py agents/legal_agent.py prompts/legal_agent.md core/agent_factory.py \
        index.html docs/CHANGELOG.md docs/AGENTS.md

# Verify nothing unwanted is staged
git status

# Commit
git commit -m "v0.32.0 — feature: เพิ่ม Legal Agent สำหรับงานด้านกฎหมาย"

# Confirm no leftover files
git status
```

**Never commit:** `.env`, `data/assistant.db`, `workspace/`, `temp/`, `server.log`, `*.zip`, screenshot images, `__pycache__/`.

---

## 13. Common Pitfalls

### Calling `get_workspace()` inside a loop

`get_workspace()` reads from a shared mutable global. If a concurrent request calls `POST /api/workspace` while your loop is running, subsequent calls will return the new workspace — potentially writing files to the wrong directory. Always capture workspace at the start of a request and pass it through:

```python
# Correct
workspace = get_session_workspace(session_id) or get_workspace()
for item in items:
    do_something(workspace, item)   # same workspace for all iterations

# Wrong
for item in items:
    do_something(get_workspace(), item)  # workspace might change mid-loop
```

### Forgetting `inject_date()` in a custom streaming path

If you add a new streaming path that calls the OpenAI client directly (bypassing `BaseAgent`), remember to call `inject_date(system_prompt)` before building the messages array. Without it, the agent does not know today's Thai Buddhist Era date and may produce documents with the wrong year.

### Adding a write tool to `READ_ONLY_TOOLS`

`READ_ONLY_TOOLS` is what agents receive in normal mode. Any tool in this set can be called by any agent on any user request — no additional confirmation. Write operations (creating or modifying files) must go through the explicit `handle_save()` / `handle_pm_save()` flow in `app.py`, not through an agent tool call. Never add `create_file`, `update_file`, or `delete_file` to `READ_ONLY_TOOLS`.

### Prompt changes do not hot-reload

Agent instances are cached by `AgentFactory`. `load_prompt()` is called in `__init__`, which runs only on first instantiation. Prompt file edits during development require a server restart to take effect.

### PM Agent subtask `agent` key must be one of `{hr, accounting, manager}`

The `plan()` method explicitly filters subtasks:

```python
valid_agents = {'hr', 'accounting', 'manager'}
return [s for s in subtasks if s.get('agent') in valid_agents]
```

If you add a new agent and want PM to be able to delegate to it, add its key to `valid_agents` in `PMAgent.plan()` and update `prompts/pm_agent.md` to list it as a valid sub-agent.

### Thai text in `.env` values

`python-dotenv` reads `.env` as bytes and decodes with the system locale. On some servers this is not UTF-8. Avoid Thai characters in `.env` values. If you must include Thai text (e.g., in a default message), set `PYTHONUTF8=1` in the environment before starting the server:

```bash
PYTHONUTF8=1 ./venv/bin/gunicorn --config gunicorn.conf.py "app:app"
```

`start.sh` already does this via `export PYTHONIOENCODING=utf-8`.

### `BaseAgent.run_with_tools()` max_iterations is 5

The agentic loop runs at most 5 iterations. For agents that need many sequential tool calls (e.g., reading multiple files before generating a document), the loop may exhaust without producing a final answer. If this happens, the browser receives a `status` event with "ดำเนินการครบ N รอบแล้ว กรุณาลองใหม่" — no `error` type, just a status. Increase `max_iterations` if you expect more than 4 tool calls per response. Be cautious: more iterations mean longer wait times and more API tokens.
