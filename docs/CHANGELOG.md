# Changelog

All notable changes to this project will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.32.45] — 2026-04-03

### Added
- **Partial file editing** — เลือกข้อความใน Preview Panel แล้วกด "แก้ไขส่วนนี้" เพื่อให้ AI แก้เฉพาะส่วนนั้น
- **`[PARTIAL_EDIT]` prompt marker** — Document Agent รับ marker นี้และ return เฉพาะ `[REPLACEMENT]...[/REPLACEMENT]` แทนการเขียนทั้งไฟล์
- **`POST /api/workspace/replace`** — endpoint สำหรับ find-and-replace-one ในไฟล์
- **ConfirmBar type="replace"** — ขั้นตอนยืนยันก่อนเขียนทับ รองรับคำสั่ง "เขียนทับ" หรือกดปุ่ม
- **`replaceInFile()` API** — frontend function สำหรับเรียก replace endpoint
- **Preview auto-refresh** — PreviewPanel refresh เนื้อหาอัตโนมัติหลัง replace สำเร็จ

### Fixed
- **Raw-only selection** — popup "แก้ไขส่วนนี้" ใช้ได้เฉพาะ raw view เพื่อให้ text ตรงกับไฟล์จริง
- **Text overflow** — ข้อความใน user bubble ใช้ `break-words` ป้องกัน overflow
- **Prefill key pattern** — ใช้ `{ text, key }` state แทน setText+clear เพื่อ trigger useEffect ได้ถูกต้อง
- **`.docx`/`.xlsx` binary serving** — `serve_workspace_file` แปลง markdown text เป็น binary on-the-fly

### Changed
- **AI message bubble** — ขยายเต็มความกว้าง chat column ลบ `max-w-4xl` และ `max-w-[80%]`
- **InputArea width** — ปรับ padding ให้ตรงกับ message bubble (`px-5`, ลบ `max-w-4xl`)

## [1.0.0] — 2026-03-31

### Added

- **LLM-based request routing** — Orchestrator analyzes user input and dispatches to the most appropriate specialized agent (HR, Accounting, Manager, PM, Chat, Document)
- **Six specialized agents** — Each with domain-specific system prompts loaded from `prompts/*.md` files
- **SSE streaming responses** — Real-time token-by-token output with status updates, agent identification, tool-call visibility, and web search source links
- **MCP filesystem tools** — Create, read, update, delete, and list files in a sandboxed workspace with path-traversal protection
- **Multi-format document export** — Save generated content as Markdown (.md), plain text (.txt), Word (.docx), Excel (.xlsx), or PDF (.pdf)
- **Web search integration** — Agents can search the internet via DuckDuckGo for current information (laws, tax rates, market trends)
- **Workspace management** — Switch between workspace folders, create new workspaces, list available workspaces, and stream file-change events via SSE
- **Session-based history** — Jobs grouped into sessions with full audit trail in SQLite (WAL mode); browseable at `/history`
- **PM subtask decomposition** — PM Agent breaks complex multi-domain requests into subtasks and delegates to HR, Accounting, or Manager agents sequentially
- **Confirmation flow** — Save/discard/edit workflow for generated documents; user must explicitly approve before any file is written to disk
- **Local Agent mode** — Optional standalone HTTP server (`local_agent.py`, port 7000) for direct local filesystem access from Windows machines
- **Dark and light themes** — Toggleable UI with CSS custom properties; preference saved in localStorage
- **Rate limiting** — Per-IP throttling on `/api/chat` (10/min) and `/api/delete` (20/min) via flask-limiter
- **Bilingual support** — Full Thai and English support throughout the UI, agent prompts, error messages, and documentation
- **Graceful database degradation** — If SQLite is unavailable, chat continues to work; only history is lost
- **Auto-cleanup of temp files** — Cron job removes temporary draft files older than 60 minutes every 30 minutes
- **File preview** — Preview file contents from the workspace via `/api/preview`; binary files (docx, xlsx, pdf) extracted to plain text
- **Raw file serving** — Serve workspace files directly via `/api/serve/<filename>` for PDF and image inline preview
- **Health endpoint** — `/api/health` returns model, workspace, and database status

### Changed

- **Minimum version pins in requirements.txt** — All 16 dependencies now have minimum version constraints (e.g., `flask>=3.0`, `openai>=1.30`)
- **Gunicorn default workers** — Increased from 2 to 4 for better SSE concurrency (1 worker permanently held by `/api/files/stream`)
- **Pending document size limit** — Increased from 200KB to 204800 bytes (200KB) with UTF-8 safe truncation at word boundaries
- **Overwrite filename validation** — Stricter regex (`^[\w.\-]{1,120}$`) for the `overwrite_filename` parameter
- **Session workspace isolation** — Added `set_session_workspace()` and `get_session_workspace()` for per-session workspace paths (global fallback remains)
- **Workspace state persistence** — Last-used workspace path persisted across server restarts via `data/.workspace_state`

### Fixed

- **UTF-8 truncation in pending documents** — Fixed byte-level truncation that could cut mid-character; now truncates at word boundaries with safe UTF-8 decode
- **Workspace race condition** — Workspace path is now captured once at request start and passed as a parameter, preventing concurrent workspace changes from affecting in-flight requests
- **SSE stream cleanup** — Proper `GeneratorExit` handling and queue cleanup for `/api/files/stream` SSE connections
- **Missing routes** — Added `/api/preview`, `/api/serve/<filename>`, `/api/history/<job_id>`, and `/api/workspace/new` endpoints
- **Dead code removal** — Removed unused functions and unreachable code paths identified during review
- **Session workspace wiring** — Fixed session workspace not being properly passed to PM subtask execution and file save operations
- **Global workspace mutation in PM loop** — Eliminated repeated `get_workspace()` calls inside the PM subtask loop; workspace is captured once at request start
- **Tool restriction bypass** — Added authorization check in `run_with_tools()` to verify each tool call is in the allowed set before execution
- **Double fail_job** — Fixed race condition where `fail_job()` could be called both in the exception handler and the `finally` block
- **UnicodeDecodeError gap in file reading** — Added explicit `UnicodeDecodeError` handling in `fs_read_file()` for binary files that slip past extension checks
- **Fake tool-call JSON leakage** — Server-side regex stripping of fake tool-call patterns (`{"request": "..."}`, `{"tool": "..."}`) that some models emit as plain text
- **Client-side sanitization edge cases** — Improved `_sanitizeHtml()` to handle additional XSS vectors
- **English keyword false positives** — Fixed `\b` word-boundary regex for "ok" and "save" to prevent matching inside words like "stock" or "unsaved"
- **PM subtask error cleanup** — Temp files are now properly cleaned up when a PM subtask fails mid-execution
- **Missing route for workspace file serving** — Added `/api/serve/<filename>` with path-traversal validation
- **Orchestrator empty response handling** — Added fallback to ChatAgent when Orchestrator returns empty or unparseable JSON
- **Agent factory unknown type fallback** — Unknown agent types now log a warning and fall back to ChatAgent instead of crashing
- **Database zombie job cleanup** — Jobs stuck in `pending` status for over 1 hour are automatically marked as `error` on server startup
- **WeasyPrint verbose logging** — Suppressed fontTools and WeasyPrint font subsetting logs that flooded the console
- **PDF character limit** — Added 100,000 character cap for PDF export to prevent WeasyPrint from hanging on very large documents
- **Conversation history truncation** — History entries are now truncated to 3000 characters each and limited to the last 20 messages
- **Empty LLM response retry** — Added retry logic (1 retry) for empty LLM responses caused by rate limits or transient API glitches
- **Tool argument JSON parse errors** — Added explicit error handling for malformed tool call arguments
- **Web search call rate limiting** — Capped web search tool calls at 3 per agentic loop to prevent excessive API usage
- **Max iteration exhaustion handling** — Added status message when `run_with_tools()` exhausts all iterations without finishing
- **File format inference on overwrite** — When overwriting an existing file, the output format is now inferred from the file extension (e.g., `.docx` files are re-converted properly)
- **Local Agent mode save restriction** — `handle_save()` now returns a clear error message when called in Local Agent mode (file saving is not supported in this mode)
- **Request delete marker handling** — Added proper interception of `request_delete` tool results and conversion to `delete_request` SSE events for browser confirmation modal
- **Local delete marker handling** — Added proper interception of `local_delete` tool results and conversion to `local_delete` SSE events for browser-side file removal

### Security

- **Path traversal prevention** — All file operations use `os.path.commonpath` to validate that resolved paths stay within the workspace root
- **Filename validation** — Regex-based filename validation (`^[\w.\-]{1,200}$`) on all file-related endpoints
- **Workspace root allowlisting** — Runtime workspace changes are restricted to paths under `ALLOWED_WORKSPACE_ROOTS`
- **Tool authorization** — Each tool call is verified against the allowed tool set before execution in the agentic loop
- **Rate limiting** — Per-IP throttling on chat and delete endpoints prevents abuse
- **CORS configuration** — Origins restricted to localhost variants by default; configurable via `CORS_ORIGINS` environment variable
- **Local Agent origin restriction** — `local_agent.py` only accepts requests from `localhost:5000` by default
- **Pending document size limit** — Incoming `pending_doc` content is truncated to 200KB at the byte level with safe UTF-8 decoding
- **HTML sanitization** — Client-side sanitization removes `<script>`, `<iframe>`, and `on*` event handlers from rendered Markdown
