# Bug Fixes Roadmap
**Project:** AI POC — Internal AI Assistant
**Version at time of writing:** v0.11.1
**Date:** 2026-03-26
**Author:** project-planner subagent

This document plans every known bug fix, grouped by severity and execution order.
Each item includes the exact files to touch, the specific change required, dependencies,
and complexity rating so the implementing developer can start without a meeting.

---

## Execution Order Summary

Dependencies drive this sequence. The prompt fixes in Group A are entirely independent.
The Flask/SSE fixes in Group B must land before Group C's dead-code removal (because
removing `stream_agent` while Group B is mid-flight would create merge conflicts).
Groups D and E are fully independent of each other and of Groups A–C.

```
Recommended order:
  1. Group A (prompt fixes)       — no code risk, isolated to prompts/
  2. Group B (Flask/SSE)          — touches app.py, high-value, low-risk
  3. Group C (architecture)       — touches app.py + agents/base_agent.py + core/agent_factory.py
  4. Group D (logic correctness)  — touches app.py + agents/base_agent.py
  5. Group E (performance)        — touches db.py only
```

---

## Group A — PM Subtask Bug

**Severity:** High — produces confusing user-visible output and fake tool call JSON in the stream
**Root cause (two independent problems):**

1. `prompts/pm_agent.md` rule 3 tells PM to instruct sub-agents to save files, but sub-agents
   called via `stream_response()` have no tool access. The LLM then fabricates a JSON tool call
   as plain text and emits it into the SSE stream.

2. `prompts/hr_agent.md`, `prompts/accounting_agent.md`, and `prompts/manager_agent.md` all
   unconditionally append the footer `"พิมพ์ บันทึก เพื่อบันทึกไฟล์"`. When these agents run
   as PM subtasks the footer is misleading because the PM flow (not the agent) controls saving.

---

### A1 — Remove file-save instruction from PM_PROMPT rule 3

- [ ] **Complexity:** Easy
- [ ] **File:** `prompts/pm_agent.md`
- [ ] **Change:** Replace rule 3 entirely. The current text is:

  ```
  3. กำหนดให้แต่ละ Agent บันทึกผลลัพธ์เป็นไฟล์ด้วย เช่น "...และบันทึกผลลัพธ์เป็นไฟล์ชื่อ contract_somchai.md ใน workspace"
  ```

  Replace with:

  ```
  3. อย่าสั่งให้ Agent บันทึกไฟล์ในคำสั่ง task — ระบบจะจัดการการบันทึกให้อัตโนมัติหลัง Agent สร้างเนื้อหาเสร็จ ให้ task อธิบายเฉพาะเนื้อหาที่ต้องการสร้างเท่านั้น
  ```

- [ ] **Definition of Done:** Run a PM flow request (e.g. "สร้างสัญญาจ้างและ invoice สำหรับโปรเจกต์ X"). Verify the raw SSE stream contains no JSON object resembling `{"tool": "write_file", ...}` or `{"function": ...}` inside `text` events.
- [ ] **Fallback:** If the LLM still hallucinates tool calls despite the prompt change, add a regex filter in `app.py`'s PM subtask loop (lines 443-451) to strip any chunk matching `^\s*\{.*"function"` before yielding it. This is a last resort because it treats the symptom, not the cause.
- [ ] **Depends on:** Nothing
- [ ] **Risk:** Low — prompt-only change, no code modified

---

### A2 — Add subtask mode guard to HR, Accounting, and Manager prompts

- [ ] **Complexity:** Easy
- [ ] **Files:** `prompts/hr_agent.md`, `prompts/accounting_agent.md`, `prompts/manager_agent.md`
- [ ] **Change:** The unconditional footer at the bottom of each prompt:

  ```
  หลังแสดงเอกสารแล้ว ให้ลงท้ายด้วยบรรทัดนี้เสมอ:
  "💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์"
  ```

  Must become conditional. The cleanest way that stays in the prompt layer (avoiding code changes):

  ```
  หลังแสดงเอกสารแล้ว:
  - ถ้าคำสั่งระบุว่า "[PM_SUBTASK]" ให้จบเอกสารที่บรรทัด ⚠️ disclaimer เท่านั้น อย่าเพิ่มบรรทัดแนะนำการบันทึก
  - ถ้าไม่มี "[PM_SUBTASK]" ให้ลงท้ายด้วย: "💬 ต้องการแก้ไขส่วนไหนไหม? หรือพิมพ์ **บันทึก** เพื่อบันทึกไฟล์"
  ```

- [ ] **Code change (also required):** In `app.py`, the PM subtask dispatch at line 443, change:

  ```python
  for chunk in sub_agent.stream_response(sub_task_desc, max_tokens=10000):
  ```

  to prepend a marker to the task description:

  ```python
  subtask_message = f"[PM_SUBTASK]\n{sub_task_desc}"
  for chunk in sub_agent.stream_response(subtask_message, max_tokens=10000):
  ```

  This marker tells the agent it is running in PM context so the footer conditional fires correctly.

- [ ] **Definition of Done:** In a PM flow the streamed text for each subtask must end at the `⚠️` disclaimer line with no `💬 ต้องการแก้ไข...` or `**บันทึก**` text. In a direct (non-PM) HR/Accounting/Manager call the footer must still appear.
- [ ] **Fallback:** If the LLM ignores the `[PM_SUBTASK]` signal, implement a post-processing strip in `app.py` PM loop: after collecting `full_content`, run `re.sub(r'\n💬.*บันทึก.*$', '', full_content, flags=re.MULTILINE)` before writing temp and yielding chunks.
- [ ] **Depends on:** A1 (do A1 first so the prompt file is already open)
- [ ] **Risk:** Low for prompt changes; Low-Medium for the `app.py` one-liner

---

## Group B — Critical Flask/SSE Issues

**Severity:** Critical for production; medium in dev (Flask dev server is single-threaded so the
symptoms are masked). All three fixes are in `app.py`.

---

### B1 — Wrap SSE generators with stream_with_context

- [ ] **Complexity:** Easy
- [ ] **File:** `app.py`
- [ ] **Change:** Add import at top of file:

  ```python
  from flask import stream_with_context
  ```

  Then wrap both `Response(generate(), ...)` calls:

  1. Line 470 (`/api/chat` route):
     ```python
     return Response(stream_with_context(generate()), mimetype=...)
     ```

  2. Line 545 (`/api/files/stream` route):
     ```python
     return Response(stream_with_context(generate()), mimetype=...)
     ```

- [ ] **Definition of Done:** Under Gunicorn (`gunicorn -w 2 app:app`), open two simultaneous SSE connections, send a chat request from one while the other streams. Both must complete without a `RuntimeError: Working outside of application context` in the server log.
- [ ] **Fallback:** If `stream_with_context` is not available in the installed Flask version (`pip show flask` to check — must be >= 0.9), add `with app.app_context():` at the top of each `generate()` function body. This is the older manual equivalent.
- [ ] **Depends on:** Nothing
- [ ] **Risk:** Very Low — additive change only

---

### B2 — Sanitize exception messages before sending to SSE clients

- [ ] **Complexity:** Easy
- [ ] **File:** `app.py`
- [ ] **Change:** In the outer `except Exception as e:` block at line 464:

  ```python
  except Exception as e:
      db.fail_job(job_id)
      logger.error(f"Error: {e}")
      yield format_sse({'type': 'error', 'message': str(e)})
      yield format_sse({'type': 'done'})
  ```

  Change to:

  ```python
  except Exception as e:
      db.fail_job(job_id)
      logger.error(f"Chat error: {e}", exc_info=True)
      yield format_sse({'type': 'error', 'message': 'เกิดข้อผิดพลาดภายใน กรุณาลองใหม่อีกครั้ง'})
      yield format_sse({'type': 'done'})
  ```

  Do the same in `handle_save` (line 279) and `handle_pm_save` (line 319) where `str(e)` is
  currently forwarded to `save_failed` events. The rule: log full details server-side, send
  a user-friendly Thai message client-side.

- [ ] **Definition of Done:** Trigger a deliberate error (e.g. set `OPENROUTER_API_KEY` to an invalid value, send a chat). The frontend must display a Thai error message, not a Python stack trace or API error string. The full error must appear in the server log with `exc_info=True`.
- [ ] **Fallback:** None needed — this is a straightforward string substitution.
- [ ] **Depends on:** Nothing
- [ ] **Risk:** Very Low

---

### B3 — Replace bare `except: pass` in `_cleanup_old_temp`

- [ ] **Complexity:** Easy
- [ ] **File:** `app.py`
- [ ] **Change:** Lines 234-242. Current:

  ```python
  def _cleanup_old_temp():
      cutoff = datetime.now().timestamp() - 3600
      try:
          for fname in os.listdir(TEMP_DIR):
              if fname == '.gitkeep': continue
              fpath = os.path.join(TEMP_DIR, fname)
              if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                  os.remove(fpath)
      except: pass
  ```

  Replace with:

  ```python
  def _cleanup_old_temp():
      cutoff = datetime.now().timestamp() - 3600
      try:
          for fname in os.listdir(TEMP_DIR):
              if fname == '.gitkeep': continue
              fpath = os.path.join(TEMP_DIR, fname)
              try:
                  if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                      os.remove(fpath)
              except OSError as e:
                  logger.warning(f"[cleanup_temp] Could not remove {fname}: {e}")
      except OSError as e:
          logger.warning(f"[cleanup_temp] Could not list temp dir: {e}")
  ```

  The outer try catches `os.listdir` failure (temp dir missing). The inner try catches
  individual file removal failure. Both log a warning. Neither swallows `KeyboardInterrupt`,
  `SystemExit`, or `MemoryError`.

- [ ] **Definition of Done:** Remove write permission from `temp/` during dev server run, send a chat. Verify `[cleanup_temp]` warning appears in log and the SSE stream still completes (no crash).
- [ ] **Fallback:** None needed.
- [ ] **Depends on:** Nothing
- [ ] **Risk:** Very Low

---

## Group C — Architecture Issues

**Severity:** Medium — not crashing production today, but these are landmines for future changes.

---

### C1 — Add thread lock to AgentFactory.get_agent

- [ ] **Complexity:** Easy
- [ ] **File:** `core/agent_factory.py`
- [ ] **Change:** The current check-then-act pattern on `cls._agents` is a race condition under
  threaded Flask. Two simultaneous requests for the same new agent type both pass the
  `if agent_type not in cls._agents:` check and both instantiate the agent. The second
  write wins silently, but any mutable state built during `__init__` is duplicated.

  Change:

  ```python
  class AgentFactory:
      _agents = {}
  ```

  To:

  ```python
  import threading

  class AgentFactory:
      _agents = {}
      _lock = threading.Lock()
  ```

  And wrap `get_agent`:

  ```python
  @classmethod
  def get_agent(cls, agent_type):
      agent_type = agent_type.lower().strip()
      if agent_type in cls._agents:          # fast path, no lock
          return cls._agents[agent_type]
      with cls._lock:
          if agent_type not in cls._agents:  # double-checked locking
              if agent_type == 'hr':
                  cls._agents[agent_type] = HRAgent()
              elif agent_type == 'accounting':
                  cls._agents[agent_type] = AccountingAgent()
              elif agent_type == 'manager':
                  cls._agents[agent_type] = ManagerAgent()
              elif agent_type == 'pm':
                  cls._agents[agent_type] = PMAgent()
              elif agent_type == 'chat':
                  cls._agents[agent_type] = ChatAgent()
              else:
                  if 'chat' not in cls._agents:
                      cls._agents['chat'] = ChatAgent()
                  return cls._agents['chat']
          return cls._agents[agent_type]
  ```

- [ ] **Definition of Done:** Under `ab -n 200 -c 20` (Apache Bench) against `/api/health` with simultaneous chat requests, no `KeyError` or duplicate-construction log entries appear.
- [ ] **Fallback:** If Python's GIL makes the race benign in CPython for this specific pattern, the fix is still correct and has zero downside. There is no fallback needed — just apply the fix.
- [ ] **Depends on:** Nothing
- [ ] **Risk:** Very Low

---

### C2 — Remove dead `stream_agent` function

- [ ] **Complexity:** Easy
- [ ] **File:** `app.py`
- [ ] **Change:** `stream_agent()` (lines 244-259) is defined at module level but never called
  from any route. `handle_revise()` calls it on line 287, but `handle_revise` itself is only
  called within the `generate()` function for the edit flow. The issue is that `handle_revise`
  bypasses `BaseAgent.run_with_tools` and calls the standalone `stream_agent` directly —
  meaning revisions do not go through the agent instance's properly configured system prompt
  or tool allow-list enforcement.

  **Step 1:** Update `handle_revise` (lines 282-288) to use `AgentFactory` and `BaseAgent`:

  ```python
  def handle_revise(pending_doc: str, pending_agent: str, instruction: str, workspace: str):
      agent_instance = AgentFactory.get_agent(pending_agent)
      yield format_sse({'type': 'agent', 'agent': pending_agent, 'reason': 'แก้ไขเอกสาร'})
      yield format_sse({'type': 'status', 'message': f'{agent_instance.name} กำลังแก้ไขเอกสาร...'})
      revise_message = (
          f"แก้ไขเอกสารต่อไปนี้ตามคำสั่งที่ได้รับ\n\n"
          f"คำสั่งแก้ไข: {instruction}\n\nเอกสารเดิม:\n{pending_doc}"
      )
      for chunk in agent_instance.stream_response(revise_message, max_tokens=10000):
          yield format_sse({'type': 'text', 'content': chunk})
  ```

  **Step 2:** Delete the `stream_agent` function (lines 244-259). Verify no other call sites exist
  with `grep -n "stream_agent" app.py` before deleting.

  **Note on duplicate `done` events:** The current `handle_revise` yields pre-formatted SSE
  strings (e.g. `format_sse({'type': 'agent', ...})`) which are then yielded again by the
  caller in `generate()`. This does not produce duplicate `done` events currently, but the
  architecture is fragile — `generate()` manually collects `text` chunks from the pre-formatted
  strings (lines 404-408) by parsing `sse.startswith('data: ')`, which will silently break if
  `format_sse` ever changes its prefix. The updated `handle_revise` above solves this by
  yielding dicts instead of pre-formatted strings, matching the pattern used by `run_with_tools`.
  The caller in `generate()` must be updated to match:

  ```python
  # In generate(), replace lines 402-409:
  text_chunks = []
  for sse_data in handle_revise(pending_doc, pending_agent, user_input, workspace):
      yield sse_data  # sse_data is now a dict, format_sse called by generate()
      if isinstance(sse_data, dict) and sse_data.get('type') == 'text':
          text_chunks.append(sse_data.get('content', ''))
  ```

  Wait — `generate()` uses `yield format_sse(sse_data)` for agent data but `yield sse` for
  revise data. To keep consistency, `handle_revise` should yield dicts and the caller wraps
  with `format_sse`. Check the existing pattern in `generate()` at lines 458-460 for the model.

- [ ] **Definition of Done:** `grep -n "stream_agent" app.py` returns zero results. Edit-intent flow (user types "แก้ตรงชื่อ") still produces a revised document. Server log shows the correct agent name during revision.
- [ ] **Fallback:** If the refactor of `handle_revise` introduces bugs, revert only `handle_revise` to call `stream_agent` until the root cause is found — but do not add `stream_agent` back as a public function; make it a private `_stream_agent_direct` with a deprecation comment.
- [ ] **Depends on:** B1 (do `stream_with_context` first to avoid touching the same `Response()` line twice)
- [ ] **Risk:** Medium — the edit flow is exercised in production; manual testing of the full edit-and-save cycle is required after this change

---

### C3 — Add timeout to OpenAI client

- [ ] **Complexity:** Easy
- [ ] **File:** `core/shared.py`
- [ ] **Change:** Lines 35-38. Current:

  ```python
  client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=OPENROUTER_API_KEY,
  )
  ```

  Change to:

  ```python
  client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=OPENROUTER_API_KEY,
      timeout=60.0,
  )
  ```

  `timeout=60.0` applies to all requests made through this client including streaming.
  For streaming, it is the time to receive the first byte (connect + first chunk). If
  a response is actively streaming but slow, it will not be cut off — the timeout applies
  to the initial connection and the first response, not to the total stream duration.
  If a tighter per-request override is needed later, pass `timeout=` directly to
  `client.chat.completions.create()`.

- [ ] **Definition of Done:** With a mock that delays the first byte by 70 seconds, the server log must show an `APITimeoutError` (already imported in `app.py` line 3) within ~60 seconds, and the SSE stream must emit the Thai error message from B2 rather than hanging forever.
- [ ] **Fallback:** If 60 seconds is too short for large document generation with slow models, increase to `120.0`. The value must be in `.env` or a config constant, not hardcoded — add `OPENROUTER_TIMEOUT=60` to `.env.example` and read it: `timeout=float(os.getenv('OPENROUTER_TIMEOUT', '60'))`.
- [ ] **Depends on:** Nothing (but deploy alongside B2 so the timeout error surfaces a clean Thai message)
- [ ] **Risk:** Low — additive, no behavior change unless requests actually exceed the timeout

---

## Group D — Logic/Correctness Issues

**Severity:** Medium — causes silent wrong behavior visible to users

---

### D1 — Fix `_is_save_intent` substring false positives

- [ ] **Complexity:** Medium
- [ ] **File:** `app.py`
- [ ] **Change:** The current implementation (lines 195-198) uses `any(kw in msg for kw in _SAVE_KEYWORDS)`.
  This means `"ok"` matches inside `"โอเค"`, `"ตกลง"` matches inside `"ไม่ตกลง"`, and
  `"save"` matches inside `"don't save"`.

  The `_SAVE_NEGATIVE_PREFIX` guard only checks if the full message *starts with* a negative
  prefix, so `"ผมไม่แน่ใจ ok ไหม"` still triggers save.

  Replace the function with word-boundary-aware matching for Latin keywords and exact-token
  matching for Thai keywords:

  ```python
  import re as _re

  _SAVE_KEYWORDS_EXACT_THAI = {'บันทึก', 'เซฟ', 'ยืนยัน', 'ตกลง', 'ได้เลย', 'โอเค', 'บันทึกได้', 'บันทึกเลย', 'บันทึกได้เลย', 'ใช้ได้'}
  _SAVE_KEYWORDS_LATIN = {'ok', 'save'}
  _SAVE_NEGATIVE_TOKENS = {'ไม่', 'not', "don't", "dont", 'no', 'ไม่ใช่', 'ไม่ใช้'}

  def _is_save_intent(message: str) -> bool:
      msg = message.lower().strip()
      tokens = set(_re.split(r'[\s,\.!?]+', msg))
      # Reject if any negative modifier is present
      if tokens & _SAVE_NEGATIVE_TOKENS:
          return False
      # Thai exact token match
      if tokens & _SAVE_KEYWORDS_EXACT_THAI:
          return True
      # Latin word-boundary match
      for kw in _SAVE_KEYWORDS_LATIN:
          if _re.search(rf'\b{_re.escape(kw)}\b', msg):
              return True
      return False
  ```

  Also update `_SAVE_KEYWORDS` at line 190 to remove the old set (or keep it as alias for
  backward compatibility in case other code references it — check with `grep -n "_SAVE_KEYWORDS"
  app.py`). Based on reading the file, `_SAVE_KEYWORDS` is only referenced in `_is_save_intent`,
  so it can be removed entirely once the function is replaced.

- [ ] **Definition of Done:** Unit-test the following cases manually or via `test_cases.py`:
  - `"บันทึก"` → True
  - `"ไม่บันทึก"` → False
  - `"don't save"` → False
  - `"ok"` → True
  - `"โอเค ไม่ใช่"` → False
  - `"ผมคิดว่า ok นะ"` → True (user explicitly said ok)
  - `"บันทึกได้เลย"` → True
- [ ] **Fallback:** If the regex approach introduces new regressions, add an explicit override list:
  `_SAVE_FORCE_FALSE = {'ไม่บันทึก', "don't save", 'no save', 'ไม่ต้องบันทึก'}` and check it
  before the positive match. This is a targeted blocklist rather than a full replacement.
- [ ] **Depends on:** Nothing
- [ ] **Risk:** Medium — the save-intent matching is used in the hot path for every single request;
  test all edge cases before deploying. If regressions appear in the test suite, revert and
  apply the fallback.

---

### D2 — Handle `GeneratorExit` in `BaseAgent.run_with_tools`

- [ ] **Complexity:** Medium
- [ ] **File:** `agents/base_agent.py`
- [ ] **Change:** When a client disconnects mid-stream, Python raises `GeneratorExit` inside the
  generator. Currently `run_with_tools` has no `try/finally` block, so the OpenAI streaming
  connection continues consuming tokens and network bandwidth until the current LLM call
  finishes naturally.

  Wrap the main agentic loop:

  ```python
  def run_with_tools(self, user_message, workspace, tools, history=None, max_tokens=8000, max_iterations=5):
      messages = [
          {"role": "system", "content": self.system_prompt},
          *(history or []),
          {"role": "user", "content": user_message}
      ]

      web_search_calls = 0
      MAX_WEB_SEARCH_CALLS = 3

      try:
          for iteration in range(max_iterations):
              # ... existing loop body unchanged ...
              pass
      except GeneratorExit:
          logger.info(f"[{self.name}] Client disconnected — stopping tool loop")
          return
  ```

  Similarly, wrap `stream_response`:

  ```python
  def stream_response(self, message, history=None, max_tokens=8000):
      messages = [...]
      try:
          stream = self.client.chat.completions.create(...)
          for chunk in stream:
              if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                  yield chunk.choices[0].delta.content
      except GeneratorExit:
          logger.info(f"[{self.name}] Client disconnected during stream_response")
          return
  ```

  Note: `GeneratorExit` cannot be caught with a bare `except Exception` — it inherits from
  `BaseException`, not `Exception`. The explicit `except GeneratorExit` is required.

- [ ] **Definition of Done:** Open a chat request, close the browser tab after 2 seconds. Check
  the server log — the agent name must appear with the disconnect message within a few seconds
  of the tab close. OpenRouter API credits billed should stop increasing.
- [ ] **Fallback:** If `GeneratorExit` handling is too invasive for this release, add it only to
  the outer `for iteration in range(max_iterations)` level, not inside individual LLM call
  loops. This catches the disconnect at the next iteration boundary rather than immediately,
  but still prevents runaway multi-iteration agentic loops after disconnect.
- [ ] **Depends on:** Nothing (independent of all other groups)
- [ ] **Risk:** Low-Medium — the change is additive (new except clause). The risk is accidentally
  swallowing legitimate `BaseException` subclasses; the explicit `except GeneratorExit` avoids
  this.

---

## Group E — Performance

**Severity:** Low in production (SQLite N+1 is fast for 50 rows), but will degrade at scale.

---

### E1 — Fix N+1 queries in `db.get_history`

- [ ] **Complexity:** Easy
- [ ] **File:** `db.py`
- [ ] **Change:** Lines 210-242. The current implementation issues 1 query for jobs + 1 query
  per job for files = 51 queries for 50 jobs.

  Replace with a single JOIN query and post-process in Python:

  ```python
  def get_history(limit: int = 50) -> list:
      if not DB_AVAILABLE:
          return []
      try:
          with _connect() as conn:
              rows = conn.execute(
                  """SELECT
                       j.id, j.created_at, j.session_id, j.user_input,
                       j.agent, j.reason, j.status, j.output_text,
                       f.filename, f.agent AS file_agent, f.size_bytes,
                       f.created_at AS file_created_at
                     FROM (
                       SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?
                     ) j
                     LEFT JOIN saved_files f ON f.job_id = j.id
                     ORDER BY j.created_at DESC, f.created_at""",
                  (limit,)
              ).fetchall()

              jobs_map = {}
              order = []
              for row in rows:
                  job_id = row['id']
                  if job_id not in jobs_map:
                      order.append(job_id)
                      jobs_map[job_id] = {
                          'id': row['id'],
                          'created_at': row['created_at'],
                          'session_id': row['session_id'],
                          'user_input': row['user_input'],
                          'agent': row['agent'],
                          'reason': row['reason'],
                          'status': row['status'],
                          'output_text': row['output_text'],
                          'files': []
                      }
                  if row['filename']:
                      jobs_map[job_id]['files'].append({
                          'filename': row['filename'],
                          'agent': row['file_agent'],
                          'size_bytes': row['size_bytes'],
                          'created_at': row['file_created_at']
                      })
              return [jobs_map[jid] for jid in order]

      except Exception as e:
          logger.warning(f"[db] get_history failed: {e}")
          return []
  ```

  The subquery `SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?` ensures the limit applies
  to jobs, not to the joined rows. Without the subquery, `LIMIT ?` on the outer query would
  cut across file rows rather than job rows.

- [ ] **Definition of Done:**
  - `get_history(50)` returns the same data structure as before (verified by comparing output
    on a populated DB before and after the change).
  - A job with zero saved files still appears in the result with `'files': []`.
  - A job with 3 saved files returns all 3 in the `files` list.
  - Query count as measured by `conn.set_trace_callback(print)` drops to 1 for any limit value.
- [ ] **Fallback:** If the JOIN query introduces correctness issues on edge cases (e.g. jobs with
  many files causing row explosion that trips the `LIMIT` subquery), revert to the N+1 approach
  and instead add `CREATE INDEX IF NOT EXISTS idx_files_job_id ON saved_files(job_id)` to the
  schema in `init_db()`. The index already exists (line 80 of `db.py`) — so the N+1 is already
  indexed and the performance at 50 jobs is acceptable as a fallback position.
- [ ] **Depends on:** Nothing
- [ ] **Risk:** Low — the change is isolated to `db.py`, the output shape is identical, and
  `db.py` has graceful degradation so a bug here degrades to `[]` without crashing the app.

---

## Checklist: All Fixes by File

Use this as a quick-reference for PR reviews and merge planning.

### `prompts/pm_agent.md`
- [ ] A1 — Remove file-save instruction from rule 3

### `prompts/hr_agent.md`
- [ ] A2 — Add `[PM_SUBTASK]` conditional footer guard

### `prompts/accounting_agent.md`
- [ ] A2 — Add `[PM_SUBTASK]` conditional footer guard

### `prompts/manager_agent.md`
- [ ] A2 — Add `[PM_SUBTASK]` conditional footer guard

### `app.py`
- [ ] A2 — Prepend `[PM_SUBTASK]` marker in PM subtask dispatch (line 443)
- [ ] B1 — Wrap `Response(generate(), ...)` with `stream_with_context` (lines 470, 545)
- [ ] B2 — Replace `str(e)` with Thai user message in SSE error events (lines 467, 279, 319)
- [ ] B3 — Replace bare `except: pass` in `_cleanup_old_temp` (line 242)
- [ ] C2 — Remove `stream_agent` dead code; refactor `handle_revise` to use `BaseAgent`
- [ ] D1 — Replace `_is_save_intent` with word-boundary-aware implementation

### `core/shared.py`
- [ ] C3 — Add `timeout=60.0` to OpenAI client constructor

### `core/agent_factory.py`
- [ ] C1 — Add thread lock with double-checked locking pattern

### `agents/base_agent.py`
- [ ] D2 — Add `GeneratorExit` handling in `run_with_tools` and `stream_response`

### `db.py`
- [ ] E1 — Replace N+1 `get_history` with single JOIN query

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|-----------|--------|------------|-------|
| R1 | C2 refactor breaks edit-intent flow | Medium | High | Full manual smoke test of edit flow before merge | backend-developer |
| R2 | D1 `_is_save_intent` regex regressions break save flow | Medium | High | Test all 7 enumerated cases in DoD before merge | backend-developer |
| R3 | A2 `[PM_SUBTASK]` marker ignored by LLM | Medium | Low | Apply fallback post-processing strip if marker is ineffective | backend-developer |
| R4 | C3 60s timeout too aggressive for large document models | Low | Medium | Make timeout configurable via `OPENROUTER_TIMEOUT` env var | backend-developer |
| R5 | E1 subquery JOIN returns wrong row count on edge cases | Low | Low | Compare output on populated DB before and after; easy rollback | backend-developer |

---

## Version Bump Required

When all fixes in a group are merged, bump the version in `index.html` and add a
`CHANGELOG.md` entry. Suggested grouping:

| Merge | Bump | Entry |
|-------|------|-------|
| A1 + A2 | v0.11.2 | fix: PM subtask no longer emits fake tool call JSON or save footer |
| B1 + B2 + B3 | v0.11.3 | fix: stream_with_context, sanitized error messages, cleanup error handling |
| C1 + C2 + C3 | v0.11.4 | fix: AgentFactory thread lock, remove dead stream_agent, OpenAI client timeout |
| D1 + D2 | v0.11.5 | fix: save intent word-boundary matching, GeneratorExit on disconnect |
| E1 | v0.11.6 | perf: get_history single JOIN query replaces N+1 |
