# AI Assistant — Internal POC

> A Thai-language internal AI assistant that routes natural-language requests to specialized domain agents (HR, Accounting, Manager, PM, Document, Chat), generates structured documents, and saves them to a sandboxed workspace in multiple file formats.

**Version:** See [CHANGELOG.md](CHANGELOG.md) for the latest release history
**Primary language:** Python 3.12 / Flask — all AI output is in Thai (ภาษาไทย)
**AI provider:** OpenRouter API (OpenAI-compatible, default model: `anthropic/claude-sonnet-4-5`)

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Prerequisites](#prerequisites)
3. [Getting Started](#getting-started)
4. [Project Structure](#project-structure)
5. [Environment Variables](#environment-variables)
6. [API Overview](#api-overview)
7. [Agent Overview](#agent-overview)
8. [Running Tests](#running-tests)
9. [Docker / Deployment](#docker--deployment)
10. [Contributing](#contributing)
11. [License](#license)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Flask 3.x |
| WSGI server | Gunicorn 21+ with gevent workers |
| AI provider | OpenRouter API (OpenAI-compatible SDK) |
| Database | SQLite 3 with WAL mode |
| Document export | python-docx, openpyxl, WeasyPrint, markdown |
| Web search | DuckDuckGo Search (ddgs) |
| File serving | Flask `send_file` + MCP filesystem layer |
| Frontend | Vanilla HTML/CSS/JS (`index.html`) + optional Next.js frontend (`frontend/`) |
| Rate limiting | flask-limiter |
| Timezone | Asia/Bangkok via `zoneinfo` / tzdata |
| Python version | 3.12 (tested on 3.12; requires 3.10+ for `zoneinfo`) |

---

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **pip** and **venv** (included with Python 3.12)
- **Node.js 18+** and **npm** — only if you use the optional Next.js frontend in `frontend/`
- **Linux / WSL2** — the default environment is WSL2 on Ubuntu 22.04
- **apt packages** required by WeasyPrint for PDF rendering:

```bash
sudo apt-get install -y \
  libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
  libcairo2 libharfbuzz0b libffi-dev libjpeg-dev \
  libopenjp2-7 libgdk-pixbuf2.0-0 shared-mime-info fonts-thai-tlwg
```

- **OpenRouter API key** — sign up at [openrouter.ai](https://openrouter.ai) and create a key

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd ai-poc
```

### 2. Run first-time setup

This installs system packages (via apt), creates a Python virtual environment, installs all Python dependencies, creates required directories, and copies `.env.example` to `.env`.

```bash
bash setup.sh
```

### 3. Configure environment variables

```bash
nano .env
```

At minimum, set:

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

See the [Environment Variables](#environment-variables) section for the full reference.

### 4. Start the server

```bash
./start.sh
```

This starts:
- **Flask backend** (Gunicorn + gevent) on `http://localhost:5000`
- **Next.js frontend** (if `frontend/` exists) on `http://localhost:3000`

### 5. Open the application

- Chat UI: `http://localhost:5000`
- Job history: `http://localhost:5000/history`
- Health check: `http://localhost:5000/api/health`

---

## Project Structure

```
ai-poc/
├── app.py                  # Flask application — all API routes, SSE streaming, confirmation flow
├── db.py                   # SQLite persistence layer (jobs, saved_files tables)
├── mcp_server.py           # MCP filesystem tool implementations (create/read/update/delete/list)
├── converter.py            # Multi-format document export (md, txt, docx, xlsx, pdf)
├── gunicorn.conf.py        # Gunicorn worker configuration (gevent, timeouts, workers)
├── setup.sh                # First-time environment setup script
├── start.sh                # Server startup script (Flask + optional Next.js)
├── requirements.txt        # Python dependencies with minimum version pins
├── .env.example            # Environment variable template — copy to .env
├── index.html              # Main chat UI (single-file vanilla JS/CSS/HTML)
├── history.html            # Job history browser UI
│
├── core/                   # Core infrastructure modules
│   ├── shared.py           # Global config, model/client singletons, workspace state, env vars
│   ├── orchestrator.py     # LLM-based request routing (returns agent type + reason as JSON)
│   ├── agent_factory.py    # Thread-safe agent singleton factory
│   └── utils.py            # Prompt loader, SSE formatter, tool executor, web search, date injector
│
├── agents/                 # Specialized agent implementations
│   ├── base_agent.py       # BaseAgent: stream_response() and run_with_tools() agentic loop
│   ├── hr_agent.py         # HR Agent — employment documents, policies, JDs
│   ├── accounting_agent.py # Accounting Agent — invoices, budgets, financial reports
│   ├── manager_agent.py    # Manager Advisor — team management advisory
│   ├── pm_agent.py         # PM Agent — multi-domain task decomposition and delegation
│   ├── chat_agent.py       # Chat Agent — general conversation and system guidance
│   └── document_agent.py  # Document Agent — general business documents (SOP, reports, etc.)
│
├── prompts/                # System prompts loaded at agent startup
│   ├── orchestrator.md     # Routing rules and agent descriptions
│   ├── hr_agent.md         # HR Agent system prompt
│   ├── accounting_agent.md # Accounting Agent system prompt
│   ├── manager_agent.md    # Manager Advisor system prompt
│   ├── pm_agent.md         # PM Agent planning prompt (JSON output)
│   ├── chat_agent.md       # Chat Agent system prompt
│   └── document_agent.md  # Document Agent system prompt
│
├── workspace/              # Default directory for saved output files (gitignored)
├── temp/                   # Temporary draft files awaiting user confirmation (auto-cleaned)
├── data/                   # SQLite database file and workspace state
│   ├── assistant.db        # SQLite database (jobs + saved_files tables)
│   └── .workspace_state    # Persists last-used workspace path across restarts
│
├── docs/                   # Technical documentation
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── AGENTS.md
│   ├── DEPLOYMENT.md
│   ├── DEVELOPER_GUIDE.md
│   └── MANUAL.md           # Legacy developer manual (pre-v1.0)
│
├── frontend/               # Next.js frontend (runs on :3000 when available)
└── .claude/agents/         # Claude Code subagent definitions for code review automation
```

---

## Environment Variables

All variables are read from `.env` at startup via `python-dotenv`.

### Required

| Variable | Description | Example |
|---|---|---|
| `OPENROUTER_API_KEY` | API key for OpenRouter. All AI calls fail without this. | `sk-or-v1-xxx...` |

### AI Model Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_MODEL` | `anthropic/claude-sonnet-4-5` | Model identifier from [openrouter.ai/models](https://openrouter.ai/models) |
| `OPENROUTER_TIMEOUT` | `60` | API request timeout in seconds. Increase for slow models or long documents. |
| `AGENT_MAX_TOKENS` | `32000` | Max output tokens for document-generating agents (HR, Accounting, Document, PM subtasks) |
| `CHAT_MAX_TOKENS` | `8000` | Max output tokens for the Chat Agent |
| `ORCHESTRATOR_MAX_TOKENS` | `1024` | Max tokens for the Orchestrator routing call — keep this low |

### Workspace

| Variable | Default | Description |
|---|---|---|
| `WORKSPACE_PATH` | `./workspace` | Default directory for saved output files. Supports absolute and relative paths. |
| `ALLOWED_WORKSPACE_ROOTS` | _(project root)_ | Comma-separated list of root paths the runtime is allowed to use as workspaces. Blank = project root only. |
| `MAX_PENDING_DOC_BYTES` | `204800` | Maximum size of a pending document sent from the frontend in bytes (200 KB). |
| `WEB_SEARCH_TIMEOUT` | `15` | Timeout in seconds for DuckDuckGo web search calls. |

### Gunicorn / Server

| Variable | Default | Description |
|---|---|---|
| `GUNICORN_WORKERS` | `4` | Number of Gunicorn worker processes. Formula: `(2 × CPU cores) + 1`, minimum 4. |
| `GUNICORN_CONNECTIONS` | `50` | Max simultaneous greenlet connections per worker. |
| `GUNICORN_TIMEOUT` | `120` | Worker timeout in seconds. Must be higher than `OPENROUTER_TIMEOUT`. |
| `GUNICORN_LOG_LEVEL` | `info` | Log verbosity: `debug`, `info`, `warning`, `error`. |
| `FLASK_HOST` | `0.0.0.0` | IP address the server binds to. |
| `FLASK_PORT` | `5000` | Port number. |
| `FLASK_DEBUG` | `0` | Enable Flask debug mode (`1`=on). Never enable in production. |

### Rate Limiting

| Variable | Default | Description |
|---|---|---|
| `CHAT_RATE_LIMIT` | `10 per minute` | Per-IP rate limit for `/api/chat`. Uses flask-limiter syntax. |
| `RATELIMIT_STORAGE_URI` | `memory://` | Rate limit storage backend. Use `redis://localhost:6379/0` for multi-process production. |

### CORS

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:5000,...` | Comma-separated list of allowed CORS origins. |

---

## API Overview

The backend exposes a REST + SSE API on port 5000. All responses use JSON except the streaming chat endpoint which uses Server-Sent Events.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a message; returns SSE stream of events |
| `GET` | `/api/health` | System health check |
| `GET` | `/api/history` | Paginated job history |
| `GET` | `/api/history/<job_id>` | Single job detail |
| `GET` | `/api/files` | List workspace files |
| `GET` | `/api/files/stream` | SSE stream of workspace change notifications |
| `GET` | `/api/preview` | Preview a file's text content |
| `GET` | `/api/serve/<filename>` | Serve raw file bytes (for PDF preview) |
| `POST` | `/api/delete` | Delete a file from workspace |
| `GET` | `/api/workspace` | Get current workspace path |
| `POST` | `/api/workspace` | Set workspace path |
| `GET` | `/api/workspaces` | List available workspace directories |
| `POST` | `/api/workspace/new` | Create a new workspace directory |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/<session_id>` | Get jobs for a session |
| `DELETE` | `/api/sessions/<session_id>` | Delete a session and all its jobs |

For full endpoint documentation including request/response schemas and examples, see [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

---

## Agent Overview

The Orchestrator analyzes each user message and routes it to the most appropriate agent:

| Agent | Key | Handles |
|---|---|---|
| HR Agent | `hr` | Employment contracts, JDs, HR policies, leave notices |
| Accounting Agent | `accounting` | Invoices, budgets, expense reports, financial statements |
| Manager Advisor | `manager` | Team feedback, headcount requests, conflict resolution |
| PM Agent | `pm` | Multi-domain requests requiring documents from multiple agents |
| Document Agent | `document` | Meeting minutes, SOPs, marketing plans, quotations, executive summaries |
| Chat Agent | `chat` | General conversation, system guidance, brainstorming |

For detailed agent documentation including system prompts, tool usage rules, and use cases, see [docs/AGENTS.md](docs/AGENTS.md).

---

## Running Tests

```bash
# Basic health and safety checks (no API calls)
./venv/bin/python3 smoke_test_phase0.py

# Main agent flow tests (requires valid OPENROUTER_API_KEY and running server)
PYTHONUTF8=1 ./venv/bin/python3 test_cases.py

# Concurrency and workspace-switch tests
./venv/bin/python3 test_concurrency_pm.py --tc 1 2 3 4

# Quick demo readiness check
./venv/bin/python3 quick-demo-check.py
```

Test files are located in the project root. They require a running server at `http://localhost:5000` except `smoke_test_phase0.py`.

---

## Docker / Deployment

The project does not include a Dockerfile as of v0.31.0. For production deployment:

1. Install system dependencies (WeasyPrint, fonts) on the host
2. Create a Python virtual environment and install `requirements.txt`
3. Configure a `.env` file with production values
4. Run with Gunicorn using `gunicorn.conf.py`
5. Put Nginx in front as a reverse proxy

Full step-by-step deployment instructions, Nginx configuration, systemd service file, and monitoring guidance are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Contributing

- Branch naming: `feature/description`, `fix/description`, `refactor/description`
- Commit format: `vX.X.X — [fix/feature/refactor/docs]: description`
- Every commit that touches backend Python must pass the `backend-python-reviewer` subagent
- Every commit with Thai-language content must pass the `thai-doc-checker` subagent
- Bump the version in `index.html` (`.version-tag` span) and add an entry to `docs/CHANGELOG.md` with every release

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) and [CHANGELOG.md](CHANGELOG.md) for the current development and release workflow.

---

## License

Internal use only. Not licensed for external distribution.
