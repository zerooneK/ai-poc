# Architecture

## System Overview

The AI Assistant Internal POC is a bilingual (Thai/English) chat-based application that uses an LLM-powered orchestrator to route user requests to specialized agents. The system runs as a Flask application served by Gunicorn with gevent workers, enabling concurrent SSE (Server-Sent Events) streaming for real-time responses.

When a user sends a message through the browser, the request flows through a confirmation-flow interceptor (which handles pending document save/discard/edit states), then to the Orchestrator which calls the LLM to determine which agent should handle the request. The selected agent — HR, Accounting, Manager, PM, Chat, or Document — processes the request using a tool-calling agentic loop that can read files, search the web, and generate content. All responses stream back to the browser as SSE events. Generated documents enter a confirmation workflow where the user must explicitly approve saving, discarding, or revising before any file is written to the workspace.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (index.html)                         │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Chat UI    │  │ File Sidebar │  │ Format Modal │  │ Workspace │ │
│  │ SSE recv   │  │ SSE/poll     │  │ (save)       │  │ Picker    │ │
│  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
└────────┼────────────────┼─────────────────┼────────────────┼───────┘
         │ POST /api/chat │ GET /api/files  │ POST /api/     │ GET /api/
         │ (SSE response) │ /stream (SSE)   │ workspace      │ workspaces
         ▼                ▼                 ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Flask Server (Gunicorn + gevent)                │
│  app.py ─── routes, SSE generator, confirmation flow                │
│                                                                     │
│  ┌───────────────────────────┐    ┌───────────────────────────────┐ │
│  │ core/orchestrator.py      │    │ core/agent_factory.py         │ │
│  │ LLM-based routing         │───▶│ Thread-safe agent cache       │ │
│  └───────────────────────────┘    └───────────┬───────────────────┘ │
│                                                │                     │
│  ┌─────────────────────────────────────────────┼───────────────────┐ │
│  │ agents/                                     │                   │ │
│  │  base_agent.py ── stream_response()         │                   │ │
│  │  hr_agent.py     ── run_with_tools()        │                   │ │
│  │  accounting_agent.py                        │                   │ │
│  │  manager_agent.py                           │                   │ │
│  │  pm_agent.py ── plan() + stream_response()  │                   │ │
│  │  chat_agent.py                              │                   │ │
│  │  document_agent.py                          │                   │ │
│  └─────────────────────────────────────────────┼───────────────────┘ │
│                                                │                     │
│  ┌──────────────────────┐  ┌───────────────────┼──────────────────┐ │
│  │ core/utils.py        │  │ mcp_server.py     │                  │ │
│  │ execute_tool()       │◄─┤ fs_create_file()  │                  │ │
│  │ load_prompt()        │  │ fs_read_file()    │                  │ │
│  │ format_sse()         │  │ fs_update_file()  │                  │ │
│  │ _web_search()        │  │ fs_delete_file()  │                  │ │
│  └──────────────────────┘  │ fs_list_files()   │                  │ │
│                            └───────────────────┼──────────────────┘ │
│                                                │                     │
│  ┌──────────────────────┐  ┌───────────────────┼──────────────────┐ │
│  │ db.py                │  │ converter.py      │                  │ │
│  │ SQLite (WAL mode)    │  │ to_docx()         │                  │ │
│  │ jobs + saved_files   │  │ to_xlsx()         │                  │ │
│  └──────────────────────┘  │ to_pdf()          │                  │ │
│                            └───────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────────────────────┐ │
│  │ core/shared.py       │  │ local_agent.py (optional, port 7000) │ │
│  │ workspace state      │  │ Standalone HTTP for local filesystem │ │
│  │ OpenAI client        │  └──────────────────────────────────────┘ │
│  └──────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────┘
         │                                     │
         ▼                                     ▼
┌──────────────────┐              ┌──────────────────────────────────┐
│ data/assistant.db│              │ OpenRouter API (LLM provider)    │
│ (SQLite WAL)     │              │ DuckDuckGo (web search)          │
└──────────────────┘              └──────────────────────────────────┘
```

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | Flask | Lightweight, sufficient for a POC; easy to add routes incrementally |
| Server | Gunicorn + gevent | gevent workers enable async I/O for SSE streaming without blocking; production-safe |
| Database | SQLite (WAL mode) | Zero-configuration, file-based; WAL mode allows concurrent reads during writes; graceful degradation built in |
| Frontend | Vanilla HTML/JS/CSS | No build step, no dependencies; self-contained SPA with marked.js for Markdown rendering |
| AI provider | OpenRouter | Model-agnostic gateway; supports Claude, Gemini, Qwen, and others via a single API key |
| File tools | MCP filesystem functions | Standardized tool interface; path-traversal protection; dual-layer (direct import + FastMCP server) |
| Document export | python-docx, openpyxl, WeasyPrint | Native Python libraries for DOCX, XLSX, and PDF; Thai font support built in |
| Web search | DuckDuckGo (ddgs) | No API key required; privacy-respecting; sufficient for POC scope |
| Rate limiting | flask-limiter | Per-IP throttling on chat and delete endpoints; in-memory storage for POC |

## Backend Structure

The backend follows a modular Flask pattern with clear separation of concerns:

- **`app.py`** — Flask application factory, all HTTP routes, SSE streaming generator, and confirmation-flow handlers (`handle_save`, `handle_revise`, `handle_pm_save`). No business logic beyond routing and flow control.
- **`core/`** — Orchestration layer. `orchestrator.py` handles LLM-based request routing. `agent_factory.py` provides thread-safe singleton agent instances via double-checked locking. `shared.py` holds global state (OpenAI client, workspace path, token limits, event bus). `utils.py` contains helper functions for prompt loading, tool execution, web search, and SSE formatting.
- **`agents/`** — Specialized agent implementations. `base_agent.py` provides the core agentic loop (`stream_response` for simple streaming, `run_with_tools` for tool-calling loops). Each domain agent (HR, Accounting, Manager, PM, Chat, Document) is a minimal subclass that loads its own system prompt.
- **`mcp_server.py`** — Two-layer filesystem tool server. Layer A exposes plain Python functions for direct import. Layer B wraps them as a FastMCP standalone server.
- **`db.py`** — SQLite persistence with graceful degradation. Every public function catches its own exceptions and returns safe defaults. DB failures never propagate to the SSE flow.
- **`converter.py`** — Multi-format document export (md, txt, docx, xlsx, pdf). All functions return bytes.

## Frontend Structure

The primary production frontend remains the single-page application in `index.html` with no build tools or frameworks:

- **HTML** — Semantic layout with sidebar (navigation, agent badges, file list), main chat area (messages, output), and input bar (textarea, send button, format selector).
- **CSS** — CSS custom properties (design tokens) for theming. Dark mode default with light mode toggle. Thai font support via Google Fonts (Sarabun).
- **JavaScript** — All logic in a single `<script>` block. Uses the `EventSource` API for SSE consumption, `fetch` for POST requests, and `marked.js` (CDN) for Markdown rendering. State is managed through module-scoped variables (no framework).

A separate `history.html` provides a job history viewer that queries `/api/history`.

There is also an in-progress Next.js frontend under `frontend/` used for the migration effort. Its file/workspace APIs are now session-scoped in the same way as the Flask chat flow, so it no longer falls back to the process-global workspace during preview, delete, file streaming, or workspace switching.

## Data Flow

### Standard Request (Single Agent)

1. User types a message and clicks Send.
2. Browser POSTs to `/api/chat` with `{ message, conversation_history, session_id, ... }`.
3. Flask creates a job record in SQLite (status: `pending`).
4. The `generate()` SSE generator captures the workspace path once (to avoid global state races).
5. `Orchestrator.route()` calls the LLM with the user message and returns `(agent_type, reason)`.
6. `AgentFactory.get_agent(agent_type)` returns a cached agent instance.
7. The agent runs `run_with_tools()` — an agentic loop of up to 5 iterations:
   - Each iteration calls the LLM with streaming enabled.
   - Text deltas are yielded as SSE `text` events.
   - If the LLM requests a tool call, `execute_tool()` runs it and the result is fed back to the LLM.
   - The loop exits when no tool calls remain.
8. The job is marked `completed` in the database.
9. A `done` SSE event signals the browser to render the final Markdown and update pending state.

### PM Multi-Agent Request

1. Orchestrator routes to `pm`.
2. `PMAgent.plan()` calls the LLM (non-streaming, JSON response) to decompose the request into subtasks.
3. Each subtask is assigned to an agent (hr, accounting, or manager).
4. Sub-agents run `stream_response()` sequentially. Each output is written to a temp file.
5. `pending_file` SSE events inform the browser of staged files.
6. The user confirms save, selects formats per file, and `handle_pm_save()` moves/converts all files to the workspace.

### Confirmation Flow

When an agent generates a document, the content is held in `pending_doc` (single agent) or `pending_temp_paths` (PM). The user must explicitly:
- **Save** — triggers `handle_save()` or `handle_pm_save()`, which writes the file to the workspace.
- **Discard** — marks the job as `discarded` and cleans up temp files.
- **Edit** — triggers `handle_revise()`, which sends the document plus revision instructions back to the agent.

## Key Design Decisions

- **Graceful degradation in db.py** — Every database function catches its own exceptions. If SQLite is unavailable, the chat still works; only history is lost.
- **Per-session workspace isolation (strengthened in v0.32.7)** — All workspace-sensitive routes now resolve the effective workspace through the same session-aware path as `chat()`: health, file listing, file-change SSE, preview, raw file serving, delete, workspace read, workspace set, and workspace creation. If a client supplies an invalid `session_id`, the server returns `400` instead of silently falling back to the global workspace.
- **Workspace captured once per request** — The workspace path is captured at the start of `generate()` and passed as a parameter. This avoids a race condition where a concurrent workspace change would affect an in-flight request.
- **Read-only tools for agents** — Agents receive `READ_ONLY_TOOLS` (list_files, read_file, web_search). Write operations (create_file, update_file, delete_file) are only available through the confirmation flow in `app.py`, ensuring user approval before any file modification.
- **SSE event bus** — Workspace changes trigger notifications through a queue-based event bus (`_ws_change_queues`), allowing multiple SSE clients watching `/api/files/stream` to receive real-time updates.
- **Double-checked locking in AgentFactory** — Agent instances are cached and created lazily with thread-safe double-checked locking, avoiding unnecessary lock contention on the fast path.

## Known Limitations

- **No authentication** — The application has no login or role-based access control. Anyone with network access to port 5000 can use it.
- **Session workspace dict unbounded** — The `_session_workspaces` dictionary grows without TTL eviction. At very high session counts (thousands of concurrent sessions), memory usage could increase. In practice this is not an issue for POC-scale usage.
- **Single LLM provider** — The system depends entirely on OpenRouter. If the API is unavailable, all features stop working. There is no fallback model or offline mode.
- **No formal test framework** — Tests are script-based integration tests (`test_cases.py`, `smoke_test_phase0.py`) that require the server to be running. No pytest or unittest configuration exists.
- **No linting or formatting tools** — No pylint, flake8, black, or mypy is configured. Code style relies on manual consistency.
- **PDF character limit** — PDF export is capped at 100,000 characters to prevent WeasyPrint from hanging on very large documents.
- **Local Agent mode is Windows-only** — The standalone `local_agent.py` server is designed for Windows users who want direct local filesystem access. It requires manual startup and is not integrated into the main deployment flow.
- **No authentication** remains the largest security gap — session-scoped workspaces prevent accidental cross-session mixing inside the app, but they do not replace real user authentication or authorization.
- Session history management now includes explicit deletion through the Flask API, with SQLite cleanup for both `jobs` and related `saved_files` records.
