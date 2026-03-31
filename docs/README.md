# AI Assistant — Internal POC

> A bilingual (Thai/English) AI-powered internal assistant that routes user requests to specialized agents (HR, Accounting, Manager, PM, Chat, Document) using an LLM orchestrator, with SSE streaming responses, file operations via MCP tools, and multi-format document export.

## Features

- **LLM-based request routing** — An orchestrator analyzes each user message and dispatches it to the most appropriate specialized agent
- **Six specialized agents** — HR, Accounting, Manager Advisor, Project Manager, Chat/Assistant, and Document generation
- **SSE streaming responses** — Real-time token-by-token output with status updates, agent identification, and tool-call visibility
- **MCP filesystem tools** — Create, read, update, delete, and list files in a sandboxed workspace with path-traversal protection
- **Multi-format document export** — Save generated content as Markdown, plain text, DOCX, XLSX, or PDF
- **Web search integration** — Agents can search the internet via DuckDuckGo for current information
- **Workspace management** — Switch between workspace folders, create new workspaces, and stream file-change events via SSE
- **Session-based history** — Jobs are grouped into sessions with full audit trail in SQLite
- **PM subtask decomposition** — The PM Agent breaks complex requests into subtasks and delegates to HR, Accounting, or Manager agents
- **Confirmation flow** — Save/discard/edit workflow for generated documents before they are written to disk
- **Local Agent mode** — Optional standalone HTTP server (port 7000) for direct local filesystem access
- **Dark and light themes** — Toggleable UI with full Thai font support (Sarabun)
- **Rate limiting** — Per-IP throttling on chat and delete endpoints

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ / Flask 3.0+ |
| Server | Gunicorn 21.2+ with gevent workers |
| Database | SQLite 3 (WAL mode) |
| Frontend | Vanilla HTML/JS/CSS SPA (no framework) |
| AI | OpenRouter API (OpenAI-compatible) |
| Export | python-docx, openpyxl, WeasyPrint, markdown |
| Search | DuckDuckGo (ddgs) |
| MCP | Filesystem tools via mcp_server.py |

## Prerequisites

- Python 3.11 or later
- System libraries for PDF export: `libpango`, `libcairo2`, `libharfbuzz`, `libffi`, `libjpeg`, `libopenjp2`, `fonts-thai-tlwg`
- An OpenRouter API key (get one at https://openrouter.ai/keys)

## Quick Start

### 1. Clone and install

```bash
cd ai-poc
bash setup.sh
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env
```

Set at minimum:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Start the server

```bash
./start.sh
```

The server runs at **http://localhost:5000**. Job history is available at **http://localhost:5000/history**.

## Running Tests

All tests require the server running on `localhost:5000`.

```bash
# Basic health check (no external dependencies)
python smoke_test_phase0.py

# Full integration tests (routed-agent flow, SSE parsing)
python test_cases.py

# PM Agent concurrency scenarios
python test_concurrency_pm.py --tc 1 2 3 4

# Demo readiness check
python quick-demo-check.py
```

Exit code `0` means all tests passed; `1` means at least one failure.

## Project Structure

```
ai-poc/
├── app.py                    # Flask app, SSE streaming, all routes
├── db.py                     # SQLite persistence (jobs + saved_files)
├── converter.py              # Multi-format export (md/txt/docx/xlsx/pdf)
├── mcp_server.py             # MCP filesystem tools (Layer A + Layer B)
├── local_agent.py            # Standalone HTTP server for local workspace (port 7000)
├── gunicorn.conf.py          # Gunicorn config (gevent, SSE-compatible)
├── setup.sh                  # First-time environment setup
├── start.sh                  # Server startup script
├── requirements.txt          # 16 packages with minimum version pins
├── .env.example              # Environment variable template
├── index.html                # Frontend SPA (Vanilla HTML/JS/CSS)
├── history.html              # Job history page
├── core/                     # Orchestration layer
│   ├── orchestrator.py       # LLM-based routing to specialized agents
│   ├── agent_factory.py      # Thread-safe agent factory
│   ├── shared.py             # Shared state: client, model, workspace, token limits
│   └── utils.py              # Helpers: load_prompt, execute_tool, web_search, format_sse
├── agents/                   # Specialized agent implementations
│   ├── base_agent.py         # BaseAgent — streaming + tool-calling agentic loop
│   ├── hr_agent.py           # HRAgent
│   ├── accounting_agent.py   # AccountingAgent
│   ├── manager_agent.py      # ManagerAgent
│   ├── pm_agent.py           # PMAgent — plan() for subtask decomposition
│   ├── chat_agent.py         # ChatAgent
│   └── document_agent.py     # DocumentAgent
├── prompts/                  # System prompts as .md files (one per agent + orchestrator)
├── workspace/                # Saved output files
├── temp/                     # Temporary draft files (cleaned by cron)
├── data/                     # SQLite database (assistant.db)
└── docs/                     # Design documentation
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key for LLM access |
| `OPENROUTER_MODEL` | No | `anthropic/claude-sonnet-4-5` | Model identifier on OpenRouter |
| `OPENROUTER_TIMEOUT` | No | `60` | API request timeout in seconds |
| `AGENT_MAX_TOKENS` | No | `32000` | Max output tokens for document agents |
| `CHAT_MAX_TOKENS` | No | `8000` | Max output tokens for chat agent |
| `ORCHESTRATOR_MAX_TOKENS` | No | `1024` | Max output tokens for orchestrator routing |
| `WORKSPACE_PATH` | No | `./workspace` | Default workspace directory |
| `ALLOWED_WORKSPACE_ROOTS` | No | project root | Comma-separated allowed workspace root paths |
| `MAX_PENDING_DOC_BYTES` | No | `204800` | Max pending document size from frontend (bytes) |
| `WEB_SEARCH_TIMEOUT` | No | `15` | DuckDuckGo search timeout in seconds |
| `GUNICORN_WORKERS` | No | `2` | Number of gevent workers |
| `GUNICORN_CONNECTIONS` | No | `50` | Max concurrent SSE connections per worker |
| `GUNICORN_TIMEOUT` | No | `120` | Worker timeout (must exceed OPENROUTER_TIMEOUT) |
| `GUNICORN_LOG_LEVEL` | No | `info` | Log level: debug, info, warning, error |
| `CHAT_RATE_LIMIT` | No | `10 per minute` | Per-IP rate limit for /api/chat |
| `RATELIMIT_STORAGE_URI` | No | `memory://` | Rate limiter storage backend |
| `FLASK_DEBUG` | No | `0` | Flask debug mode (0 or 1) |
| `FLASK_HOST` | No | `0.0.0.0` | Server bind address |
| `FLASK_PORT` | No | `5000` | Server bind port |

## License

Internal POC — not for external distribution.
