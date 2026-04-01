# Execution Summary

## Project

**AI Assistant — Internal POC** — A bilingual (Thai/English) AI-powered internal assistant that routes user requests to specialized agents (HR, Accounting, Manager, PM, Chat, Document) using an LLM orchestrator, with SSE streaming responses, file operations via MCP tools, and multi-format document export.

## Build Overview

| Item | Detail |
|---|---|
| Date | 2026-04-01 |
| Backend Framework | Flask 3.0+ with Gunicorn 21.2+ (gevent workers) |
| Frontend Framework | Vanilla HTML/JS/CSS SPA (no framework) |
| Database | SQLite 3 (WAL mode) |
| Auth | None (internal POC) |
| Test Framework | Script-based integration tests (no pytest/unittest) |

## Features Built

| Feature | Status |
|---|---|
| LLM-based request routing via Orchestrator | ✅ Implemented |
| Six specialized agents (HR, Accounting, Manager, PM, Chat, Document) | ✅ Implemented |
| SSE streaming responses with real-time token output | ✅ Implemented |
| MCP filesystem tools (create, read, update, delete, list) | ✅ Implemented |
| Multi-format document export (md, txt, docx, xlsx, pdf) | ✅ Implemented |
| Web search integration (DuckDuckGo) | ✅ Implemented |
| Workspace management (switch, create, list, stream changes) | ✅ Implemented |
| Session-based history with SQLite persistence | ✅ Implemented |
| PM subtask decomposition and multi-agent orchestration | ✅ Implemented |
| Confirmation flow (save/discard/edit) | ✅ Implemented |
| Local Agent mode (standalone HTTP server, port 7000) | ✅ Implemented |
| Dark and light themes with Thai font support | ✅ Implemented |
| Rate limiting (per-IP on chat and delete endpoints) | ✅ Implemented |
| Job history viewer page (`/history`) | ✅ Implemented |
| File preview and raw file serving | ✅ Implemented |
| Health check endpoint | ✅ Implemented |
| Auto-cleanup of temporary files (cron) | ✅ Implemented |

## Code Quality Review

| Metric | Score |
|---|---|
| Architecture | 8/10 |
| Readability | 8/10 |
| Maintainability | 8/10 |
| Security | 7/10 |

The codebase is in good shape after 29 bug fixes across three rounds. All Critical and High severity issues have been resolved. Three Medium issues remain (two client-side sanitization edge cases and one dead function), none of which block documentation generation. The architecture is clean, security controls are comprehensive, and the SSE streaming pipeline is stable.

## Testing Results

- **Backend:** `python -m py_compile ...` passed for the modified backend files, and `test_workspace_isolation.py` passed against a live Flask server. `smoke_test_phase0.py` was updated to remove Windows-only path assumptions, but the LLM-dependent chat scenarios were not re-run in this change set.
- **Frontend:** `npm run lint` passed. `npm run build` was blocked by sandbox network restrictions because `next/font` tried to fetch Google Fonts (`Inter`, `JetBrains Mono`).
- **Frontend runtime follow-up:** the React crash caused by `MessageBubble` passing both `children` and `dangerouslySetInnerHTML` was fixed, and the SSE status banner now clears when a stream ends so stale "กำลังตรวจสอบ workspace..." messages do not remain visible after the answer is complete.
- **Frontend session restore:** the Next.js sidebar session list now restores the full saved conversation for the selected session into the main chat panel instead of being a non-functional placeholder.
- **Spec coverage:** This fix set specifically added coverage for session-scoped workspace/file APIs: workspace set/get, file list, preview, delete, and file isolation across two session IDs.

## Correction Loop Log

| Phase | Iterations Used | Root Cause Summary |
|---|---|---|
| Phase 4 (Runtime) | 0 / 3 | None — no runtime errors encountered |
| Phase 5 (Testing) | 0 / 3 | None — no test failures encountered |
| Phase 5.5 (Review) | 3 / 3 | Round 1: 3 Critical + 8 High (UTF-8 truncation, workspace race, SSE cleanup, etc.) → 20 fixes. Round 2: 2 Critical + 3 High (missing routes, dead code, session workspace wiring) → 5 fixes. Round 3: 4 High (global workspace mutation, tool restriction bypass, double fail_job, UnicodeDecodeError gap) → 4 fixes. Total: 29 fixes applied. |

## Notable Technical Decisions

- **Flask over FastAPI** — Flask was chosen for its simplicity and the team's existing familiarity. The POC scope does not require async-native features; gevent provides sufficient concurrency for SSE streaming.
- **SQLite over PostgreSQL** — SQLite with WAL mode was selected for zero-configuration deployment. The graceful degradation pattern ensures the application remains functional even if the database becomes unavailable.
- **Vanilla frontend over React/Vue** — A single HTML file with inline CSS and JS eliminates build complexity, dependency management, and deployment overhead. The trade-off is a large file (~3224 lines) but no toolchain to maintain.
- **OpenRouter as AI gateway** — Using OpenRouter instead of a direct provider API allows model switching without code changes. The default model (Claude Sonnet 4.5) can be changed via a single environment variable.
- **Read-only tools for agents** — Agents receive only `list_files`, `read_file`, and `web_search`. Write operations are gated behind the user confirmation flow in `app.py`, ensuring no file is modified without explicit user approval.
- **Workspace captured once per request** — To avoid a race condition where concurrent workspace changes affect in-flight requests, the effective workspace is resolved once at the start of the SSE generator and passed as a parameter throughout.
- **Session scope extended to file APIs** — In v0.32.7 the same session-aware workspace resolution now applies to preview, raw serve, delete, file list, file-change SSE, health, and workspace routes, eliminating mixed global/session behavior.

## Known Limitations

- **No authentication** — The application has no login or role-based access control. Anyone with network access to port 5000 can use it.
- **Per-session workspace isolation** — The route coverage is now consistent across chat and file APIs, but the `_session_workspaces` dict still has no TTL eviction and the system still lacks real authentication.
- **No CSRF protection** — The application does not include CSRF tokens on form submissions.
- **Single LLM provider dependency** — The system depends entirely on OpenRouter. If the API is unavailable, all features stop working.
- **No formal test framework** — Tests are script-based and require the server to be running. No pytest, unittest, or CI pipeline is configured.
- **No linting or formatting tools** — No pylint, flake8, black, or mypy is configured. Code style relies on manual consistency.
- **PDF character limit** — PDF export is capped at 100,000 characters to prevent WeasyPrint from hanging.
- **Local Agent mode is Windows-only** — The standalone `local_agent.py` server is designed for Windows users and requires manual startup.
- **Basic client-side sanitization** — The `_sanitizeHtml()` function handles common XSS vectors but is not as comprehensive as a dedicated library like DOMPurify.
- **No accessibility audit** — ARIA labels and keyboard navigation have not been formally tested.
- Added session deletion support for the Next.js sidebar, including backend cleanup of the selected session's persisted jobs and file records.
- Updated the Next.js chat flow so the sidebar session list refreshes automatically as new chat history is created.
- Added a dedicated navbar action for creating a new empty session without reloading the page.
- Converted the empty-state suggestion cards into working buttons that trigger preset chat prompts.
- Updated the Next.js chat view to display streaming assistant text incrementally instead of waiting for the full response.
- Improved session switching in the Next.js UI by adding an immediate selection state, a loading screen, and in-memory caching of restored sessions.
- Refreshed the Next.js visual design with softer surfaces, a cleaner shell, improved chat/composer styling, and a persistent theme switcher.
- Refined the redesigned UI by fixing the theme toggle sizing, reducing the new-session button footprint, and shrinking the empty-state card.
- Corrected the redesigned theme switch control so its knob no longer overflows the toggle track.
- Updated the workspace picker modal styling so the overlay is darker and the dialog body is fully opaque.
- Reconnected the Next.js save workflow to backend save events so unsaved output can be confirmed through the format modal and saved files appear in the sidebar immediately.
- Fixed a session-restore edge case so re-clicking the active sidebar session repopulates the chat if the visible conversation was previously cleared.
- Applied the same opacity/backdrop treatment to the save-format modal so background content no longer shows through it.
- Tightened session caching so an empty visible chat no longer replaces the latest session's cached history and block restoration.
- Hardened backend correctness by preventing revise/PM failure paths from being stored as completed jobs, validating more `/api/chat` inputs, guarding `/api/history` query parsing, and adding orchestrator fallback behavior.
- Hardened backend concurrency and lifecycle handling by locking lazy client initialization, stopping per-session workspace writes from persisting global state, clearing deleted-session workspace mappings, and adding heartbeat-based file-stream SSE cleanup.
