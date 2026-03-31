# AGENTS.md — Repository Guidelines for AI Coding Agents

This document describes the structure, conventions, and workflows for this Python/Flask internal AI assistant POC. Read it fully before making changes.

## Mandatory Workflow Rules

These rules apply to every change. Do not skip any step.

1. **Never touch `.env`** — This file contains real API keys and secrets. It is gitignored for a reason. Never read, modify, or reference it. Use `.env.example` as the only source of truth for environment variables.

2. **Clarify the goal before acting** — If the user's request is ambiguous, ask follow-up questions until you have a clear, unambiguous understanding of what needs to be done. Do not guess or assume.

3. **Plan in detail before changing anything** — Before writing or modifying any code, create a step-by-step plan. Identify every file that will change, what will change in each file, and any dependencies between changes. Present the plan to the user for approval before proceeding.

4. **Follow the plan — do not deviate** — Once the plan is approved, execute only what is in the plan. Do not add unplanned changes, refactor unrelated code, or "improve" things outside the scope. If you discover something that needs fixing outside the plan, report it to the user separately.

5. **Update all related documentation** — After code changes are complete, update every documentation file that references the changed behavior. This includes `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `docs/BACKEND_MANUAL.md`, `docs/USER_GUIDE.md`, `docs/EXECUTION_SUMMARY.md`, and `PROJECT_SUMMARY.md`. Never leave docs stale.

6. **Commit everything to git** — After all code and documentation changes are done, stage all modified files and create a descriptive commit using conventional commit prefixes (`fix:`, `feat:`, `docs:`, etc.). Do not leave uncommitted changes.

7. **Summarize for the user** — After the commit is done, provide a clear, simple summary of what was changed. Use plain language. List the files modified, what was changed in each, and the commit hash. Avoid technical jargon.

## Project Structure

```
ai-poc/
├── app.py                    # Flask app + SSE streaming + all routes
├── db.py                     # SQLite persistence (jobs + saved_files tables)
├── converter.py              # Multi-format export (md/txt/docx/xlsx/pdf)
├── mcp_server.py             # MCP filesystem tools (Layer A: functions, Layer B: FastMCP)
├── local_agent.py            # Standalone HTTP server for local workspace (port 7000)
├── gunicorn.conf.py          # Gunicorn config (gevent workers, SSE-compatible)
├── setup.sh                  # First-time environment setup
├── start.sh                  # Server startup script
├── requirements.txt          # 16 packages, unpinned versions
├── .env.example              # Environment variable template (Thai + English)
├── .gitignore                # Standard Python + project-specific ignores
├── index.html                # Frontend SPA (Vanilla HTML/JS/CSS)
├── history.html              # Job history page
│
├── core/                     # Orchestration layer
│   ├── orchestrator.py       # LLM-based routing to specialized agents
│   ├── agent_factory.py      # Thread-safe singleton-ish agent factory
│   ├── shared.py             # Shared state: client, model, workspace, token limits
│   └── utils.py              # Helpers: load_prompt, execute_tool, web_search, format_sse
│
├── agents/                   # Specialized agent implementations
│   ├── base_agent.py         # BaseAgent — streaming + tool-calling agentic loop
│   ├── hr_agent.py           # HRAgent (delegates to BaseAgent)
│   ├── accounting_agent.py   # AccountingAgent (delegates to BaseAgent)
│   ├── manager_agent.py      # ManagerAgent (delegates to BaseAgent)
│   ├── pm_agent.py           # PMAgent — has plan() for subtask decomposition
│   ├── chat_agent.py         # ChatAgent (delegates to BaseAgent)
│   └── document_agent.py     # DocumentAgent (delegates to BaseAgent)
│
├── prompts/                  # System prompts as .md files (one per agent + orchestrator)
├── workspace/                # Saved output files (git-tracked via .gitkeep)
├── temp/                     # Temporary draft files (cleaned by cron)
├── data/                     # SQLite database (assistant.db)
├── docs/                     # Design documentation
├── plans/                    # Feature/bug fix plans
├── backup/                   # Demo backup files
├── .claude/agents/           # Claude Code subagent definitions (12 agents)
└── .opencode/                # OpenCode AI agent/skill definitions
```

## Build, Test, and Development Commands

Always use the existing shell scripts — do not create ad hoc setup commands. The server must be running on `localhost:5000` for tests.

| Command | Description |
|---|---|
| `bash setup.sh` | Install system packages, create venv, install pip deps, scaffold `.env`, setup cron |
| `./start.sh` | Activate venv, refresh deps, run Gunicorn with gevent workers on `http://localhost:5000` |
| `python smoke_test_phase0.py` | Basic health check (no external deps, uses urllib) |
| `python test_cases.py` | Full routed-agent flow checks (uses requests, parses SSE events) |
| `python test_concurrency_pm.py --tc 1 2 3 4` | PM concurrency scenarios (4 test cases) |
| `python quick-demo-check.py` | Fast demo-readiness validation (uses requests) |

**No formal linting or formatting tools configured** — no pylint, flake8, ruff, mypy, black, or editorconfig.

**Testing:** Script-based integration tests (no pytest/unittest). Tests require server running on `localhost:5000`. Tests parse SSE events manually. Exit code `0` = all pass, `1` = any failure.

## Code Style & Naming Conventions

- **Indentation:** 4 spaces
- **Functions and modules:** `snake_case`
- **Classes:** `PascalCase` (e.g., `Orchestrator`, `BaseAgent`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Module-private items:** prefix with underscore (e.g., `_THAI_MONTHS`, `_extract_json`)
- **Imports:** grouped cleanly — stdlib, third-party, local
- **Type hints:** used sparingly (only in `db.py` and `smoke_test_phase0.py`)
- **Docstrings:** triple-quoted strings
- **Logging:** `logger.error/warning/info` with `%s`-style or f-string formatting
- **Comments:** sparse and useful; Thai comments are common
- **Section separators:** Unicode box-drawing characters, e.g., `# ─── Routes ───`
- **Helpers:** prefer small helper functions in `core/` over duplicating logic in routes or agents
- **No formatter configured** — match surrounding style

## Architecture Patterns

- **Modular Flask:** `app.py` contains routes only; business logic lives in `core/` and `agents/`
- **Factory pattern:** `AgentFactory.get_agent()` with thread-safe double-checked locking
- **Singleton-ish agents:** agent instances are cached in the factory
- **Graceful degradation:** `db.py` catches all exceptions and returns safe defaults; DB failures never propagate to SSE flow
- **SSE streaming:** all chat responses use Server-Sent Events with `stream_with_context`
- **MCP tools:** filesystem operations abstracted in `mcp_server.py` with path validation

## Error Handling

- **User-facing errors:** always in Thai
- **Server-side errors:** `logger.error/warning` with `exc_info=True`
- **Streaming contexts:** `GeneratorExit` is re-raised
- **Exception ordering:** specific exceptions caught before bare `except` (e.g., `OSError`, `ValueError`, `FileNotFoundError`)
- **Database layer:** catches all exceptions and returns safe defaults

## Security

- **Path traversal prevention:** `os.path.commonpath` checks
- **Filename validation:** regex `r'^[\w.\-]{1,200}$'`
- **Workspace root allowlisting:** `ALLOWED_WORKSPACE_ROOTS`
- **Rate limiting:** via `flask-limiter`
- **Secrets:** never commit `.env` or real API keys; load from environment via `python-dotenv`

## Testing Guidelines

This project uses **script-based integration tests** (no pytest/unittest). Tests require the server running on `localhost:5000` and parse SSE events manually.

- Add or extend top-level `test_*.py` scripts when behavior changes
- Name files after the scenario, e.g., `test_concurrency_pm.py`
- Exit code `0` = all pass, `1` = any failure
- Before opening a PR, run the smoke test plus the most relevant scenario scripts for the files you changed

## Commit & Pull Request Guidelines

- **Prefixes:** `fix:`, `feat:`, version tags like `v0.30.4`
- **Messages:** imperative, scoped to one change
- **PRs should include:** short summary, affected user flow, test commands run, screenshots for UI changes in `index.html` or browser behavior

## Adding New Agents

When adding a new specialized agent:
1. Create `agents/<name>_agent.py` — keep it minimal (6 lines if delegating to BaseAgent)
2. Add a system prompt at `prompts/<name>_agent.md`
3. Register the agent in `core/orchestrator.py` routing logic
4. Update `core/agent_factory.py` with a factory method
5. Add the agent prompt to `core/utils.py` `load_prompt()` if needed
6. Update the orchestrator prompt (`prompts/orchestrator.md`) to recognize the new agent

## Frontend Notes

- `index.html` is a single-page application using vanilla HTML/JS/CSS (no framework)
- `history.html` provides job history browsing
- Both files are self-contained — avoid introducing build tools or bundlers
- UI changes should be tested across both files for consistency

## MCP Server Architecture

- `mcp_server.py` has two layers:
  - **Layer A:** Plain Python functions for filesystem operations
  - **Layer B:** FastMCP server that exposes these functions as MCP tools
- All file operations include path validation against allowed workspace roots
- The MCP server can run standalone or be imported by other components

## Security & Configuration Tips

- Do not commit `.env` or real API keys
- Start from `.env.example`, keep `OPENROUTER_API_KEY` local
- Verify timeout-related settings when changing network or streaming behavior
- Treat files in `workspace/` and `data/` as user-facing state; avoid destructive changes without a clear migration path

## Python Version & Dependencies

- **Python 3.11+** (uses `zoneinfo`, `dict | None` type hints)
- **Dependencies** (all unpinned in `requirements.txt`): flask, flask-cors, flask-limiter, gunicorn, gevent, openai, python-dotenv, mcp, watchdog, python-docx, openpyxl, weasyprint, markdown, ddgs, tzdata, pdfplumber
