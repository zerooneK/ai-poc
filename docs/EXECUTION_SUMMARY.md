# Execution Summary

## Project

**AI Assistant — Internal POC** — A bilingual (Thai/English) AI-powered internal assistant that routes user requests to specialized agents (HR, Accounting, Manager, PM, Chat, Document) using an LLM orchestrator, with SSE streaming responses, file operations via MCP tools, and multi-format document export.

## Build Overview

| Item | Detail |
|---|---|
| Date | 2026-03-31 |
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

- **Backend:** All script-based integration tests pass. `smoke_test_phase0.py` (health check), `test_cases.py` (routed-agent flow with SSE parsing), `test_concurrency_pm.py` (4 PM concurrency scenarios), and `quick-demo-check.py` (demo readiness) all exit with code 0.
- **Frontend:** No automated frontend tests. Manual testing performed across Chrome and Firefox for UI rendering, SSE streaming, theme toggling, and modal flows.
- **Spec coverage:** All core user flows covered — single-agent document generation, PM multi-agent decomposition, save/discard/edit confirmation flow, workspace switching, file listing, and history browsing.

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
- **Workspace captured once per request** — To avoid a race condition where concurrent workspace changes affect in-flight requests, `get_workspace()` is called once at the start of the SSE generator and passed as a parameter throughout.

## Known Limitations

- **No authentication** — The application has no login or role-based access control. Anyone with network access to port 5000 can use it.
- **Global workspace state** — `WORKSPACE_PATH` is a process-level variable shared across all sessions. Per-session workspace isolation is partially implemented but the global fallback remains.
- **Single LLM provider dependency** — The system depends entirely on OpenRouter. If the API is unavailable, all features stop working.
- **No formal test framework** — Tests are script-based and require the server to be running. No pytest, unittest, or CI pipeline is configured.
- **No linting or formatting tools** — No pylint, flake8, black, or mypy is configured. Code style relies on manual consistency.
- **PDF character limit** — PDF export is capped at 100,000 characters to prevent WeasyPrint from hanging.
- **Local Agent mode is Windows-only** — The standalone `local_agent.py` server is designed for Windows users and requires manual startup.
- **Basic client-side sanitization** — The `_sanitizeHtml()` function handles common XSS vectors but is not as comprehensive as a dedicated library like DOMPurify.
- **No accessibility audit** — ARIA labels and keyboard navigation have not been formally tested.
