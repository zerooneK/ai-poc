# Backend Manual

## Overview

- **Base URL:** `http://localhost:5000`
- **Auth:** None (internal POC — no authentication layer)
- **Content-Type:** `application/json` for all POST requests
- **Streaming:** `text/event-stream` for SSE endpoints

## Response Format

### JSON Responses

```json
// Success
{ "data": ..., "message": "OK" }

// Error
{ "error": "คำอธิบายข้อผิดพลาด" }

// Success with filename
{ "success": true, "filename": "hr_contract_20260331_120000.md" }
```

### SSE Events

All SSE events follow this format:

```
data: {"type": "text", "content": "สวัสดีครับ"}

```

Each event is a JSON object with a mandatory `type` field. See the SSE Event Reference section below for all event types.

## Endpoints

### Pages

#### GET /

Serves the main frontend application (`index.html`).

**Response:** `text/html` — the SPA chat interface.

#### GET /history

Serves the job history viewer page (`history.html`).

**Response:** `text/html` — job history browser.

---

### Chat

#### POST /api/chat

Main chat endpoint. Accepts a user message and returns an SSE stream of events. Rate limited to 10 requests per minute per IP (configurable via `CHAT_RATE_LIMIT`).

**Request body:**

```json
{
  "message": "ร่างสัญญาจ้างพนักงานชื่อ สมชาย",
  "session_id": "abc-123-def",
  "conversation_history": [
    { "role": "user", "content": "สวัสดี" },
    { "role": "assistant", "content": "สวัสดีครับ มีอะไรให้ช่วยไหมครับ" }
  ],
  "pending_doc": "",
  "pending_agent": "",
  "pending_temp_paths": [],
  "output_format": "md",
  "output_formats": null,
  "overwrite_filename": null,
  "local_agent_mode": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | User input text |
| `session_id` | string | No | Session UUID for grouping jobs |
| `conversation_history` | array | No | Last 20 messages (truncated to 3000 chars each) |
| `pending_doc` | string | No | Pending document content from previous response (max 200KB) |
| `pending_agent` | string | No | Agent that created the pending document |
| `pending_temp_paths` | array | No | Temp file paths from PM subtasks awaiting save |
| `output_format` | string | No | Desired format: `md`, `txt`, `docx`, `xlsx`, `pdf` (default: `md`) |
| `output_formats` | array | No | Per-file format list for PM multi-file save |
| `overwrite_filename` | string | No | Existing filename to overwrite instead of creating new |
| `local_agent_mode` | boolean | No | If true, agents use LOCAL_AGENT_TOOLS only |

**SSE Event types returned:**

| `type` | Payload | Description |
|---|---|---|
| `status` | `{ message: string }` | Status update (e.g., "กำลังวิเคราะห์งาน...") |
| `agent` | `{ agent: string, reason: string, task?: string }` | Agent selected by orchestrator |
| `pm_plan` | `{ subtasks: [{ agent, task }] }` | PM subtask decomposition |
| `text` | `{ content: string }` | Streaming text chunk |
| `text_replace` | `{ content: string }` | Full text replacement (after fake tool-call stripping) |
| `tool_result` | `{ tool: string, result: string, filename?: string }` | Tool execution result |
| `web_search_sources` | `{ query: string, sources: [{ url, domain }] }` | Web search results with source links |
| `pending_file` | `{ temp_path: string, filename: string, agent: string }` | PM subtask temp file staged |
| `subtask_done` | `{ agent: string, index: number, total: number }` | PM subtask completed |
| `save_failed` | `{ message: string }` | Save operation failed |
| `error` | `{ message: string }` | Error occurred |
| `done` | `{}` | Response complete |
| `local_delete` | `{ filename: string }` | Local agent file deletion triggered |
| `delete_request` | `{ filename: string }` | User confirmation required for file deletion |

**Error responses (non-SSE):**

| Status | Meaning |
|---|---|
| 400 | Invalid request body or empty message |
| 429 | Rate limit exceeded |

---

### File Operations

#### POST /api/delete

Delete a file from the workspace. Rate limited to 20 requests per minute per IP.

**Request body:**

```json
{ "filename": "hr_contract_20260331_120000.md" }
```

**Response 200:**

```json
{ "success": true, "filename": "hr_contract_20260331_120000.md" }
```

**Error responses:**

| Status | Meaning |
|---|---|
| 400 | Invalid filename or file not found |

---

#### GET /api/files

List all files in the current workspace.

**Response 200:**

```json
{
  "files": [
    { "name": "hr_contract.md", "size": 2048, "modified": "2026-03-31 12:00" },
    { "name": "invoice_001.xlsx", "size": 4096, "modified": "2026-03-31 12:05" }
  ]
}
```

---

#### GET /api/files/stream

SSE endpoint for real-time workspace change notifications. Clients receive a `files_changed` event whenever a file is created, updated, or deleted in the current workspace.

**SSE events:**

```
data: {"type": "files_changed"}

```

**Response headers:** `Content-Type: text/event-stream; charset=utf-8`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive`

---

#### GET /api/preview

Preview a file's content from the workspace. Binary files (docx, xlsx, pdf) are extracted to plain text.

**Query parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file` | string | Yes | Filename to preview |

**Response 200:**

```json
{
  "filename": "hr_contract.md",
  "content": "# สัญญาจ้างงาน\n\n...",
  "ext": ".md",
  "size": 2048
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| 400 | Invalid filename |
| 403 | Path traversal attempt |
| 404 | File not found |
| 500 | File read error |

---

#### GET /api/serve/<filename>

Serve a raw file from the workspace for inline preview (PDF, images, etc.).

**Response 200:** File content with appropriate MIME type.

**Error responses:**

| Status | Meaning |
|---|---|
| 400 | Invalid filename |
| 403 | Path traversal attempt |
| 404 | File not found |

---

### History

#### GET /api/history

Get recent job history.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 50 | Maximum number of jobs to return |

**Response 200:**

```json
{
  "jobs": [
    {
      "id": "uuid-1",
      "created_at": "2026-03-31T12:00:00+00:00",
      "session_id": "abc-123",
      "user_input": "ร่างสัญญาจ้าง",
      "agent": "hr",
      "reason": "สัญญาจ้างงาน",
      "status": "completed",
      "output_text": "...",
      "files": [
        { "filename": "hr_contract.md", "agent": "hr", "size_bytes": 2048, "created_at": "..." }
      ]
    }
  ],
  "db_available": true
}
```

---

#### GET /api/history/<job_id>

Get a single job by ID.

**Response 200:**

```json
{
  "id": "uuid-1",
  "created_at": "2026-03-31T12:00:00+00:00",
  "session_id": "abc-123",
  "user_input": "ร่างสัญญาจ้าง",
  "agent": "hr",
  "reason": "สัญญาจ้างงาน",
  "status": "completed",
  "output_text": "...",
  "files": []
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| 404 | Job not found |

---

### Sessions

#### GET /api/sessions

List all sessions ordered by most recent activity.

**Response 200:**

```json
{
  "sessions": [
    {
      "session_id": "abc-123",
      "first_message": "สวัสดี",
      "last_active": "2026-03-31T12:30:00+00:00",
      "created_at": "2026-03-31T10:00:00+00:00",
      "job_count": 5,
      "last_agent": "hr"
    }
  ]
}
```

---

#### GET /api/sessions/<session_id>

Get all completed jobs for a specific session, ordered oldest first.

**Path parameters:**

| Parameter | Type | Description |
|---|---|---|
| `session_id` | string | Session UUID (8-64 alphanumeric characters and hyphens) |

**Response 200:**

```json
{
  "jobs": [
    {
      "id": "uuid-1",
      "created_at": "2026-03-31T10:00:00+00:00",
      "user_input": "สวัสดี",
      "agent": "chat",
      "output_text": "สวัสดีครับ"
    }
  ]
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| 400 | Invalid session_id format |

---

### Workspace Management

#### GET /api/workspace

Get the current workspace path.

**Response 200:**

```json
{ "workspace": "/home/user/ai-poc/workspace" }
```

---

#### POST /api/workspace

Set the workspace path. Validates against allowed workspace roots.

**Request body:**

```json
{
  "path": "/home/user/ai-poc/workspace/project-alpha",
  "session_id": "abc-123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | string | Yes | Absolute or relative path to workspace |
| `session_id` | string | No | If provided, sets per-session workspace |

**Response 200:**

```json
{ "workspace": "/home/user/ai-poc/workspace/project-alpha" }
```

**Error responses:**

| Status | Meaning |
|---|---|
| 400 | Invalid request, empty path, or path outside allowed roots |

---

#### GET /api/workspaces

List all available workspace directories under allowed roots.

**Response 200:**

```json
{
  "workspaces": [
    { "name": "project-alpha", "path": "/home/user/ai-poc/workspace/project-alpha" },
    { "name": "project-beta", "path": "/home/user/ai-poc/workspace/project-beta" }
  ]
}
```

---

#### POST /api/workspace/new

Create a new workspace directory and set it as the current workspace.

**Request body:**

```json
{ "name": "project-gamma" }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Workspace name (alphanumeric and underscore only, max 60 chars) |

**Response 201:**

```json
{ "workspace": "/home/user/ai-poc/workspace/project-gamma" }
```

**Error responses:**

| Status | Meaning |
|---|---|
| 400 | Invalid name or path outside allowed roots |

---

### Health

#### GET /api/health

Health check endpoint. Returns model, workspace, and database status.

**Response 200:**

```json
{
  "status": "ok",
  "model": "anthropic/claude-sonnet-4-5",
  "workspace": "/home/user/ai-poc/workspace",
  "db": {
    "available": true,
    "path": "/home/user/ai-poc/data/assistant.db"
  }
}
```

---

## Database Schema

### jobs

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | PK | UUID v4 job identifier |
| `created_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |
| `session_id` | TEXT | Nullable | Session UUID for grouping |
| `user_input` | TEXT | NOT NULL | Original user message |
| `agent` | TEXT | Nullable | Agent selected by orchestrator |
| `reason` | TEXT | Nullable | Routing reason from orchestrator |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' | One of: `pending`, `completed`, `error`, `discarded` |
| `output_text` | TEXT | Nullable | Full AI response text |

### saved_files

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | PK | UUID v4 file identifier |
| `job_id` | TEXT | NOT NULL, FK → jobs.id | Parent job |
| `created_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |
| `filename` | TEXT | NOT NULL | Saved filename |
| `agent` | TEXT | Nullable | Agent that created the file |
| `size_bytes` | INTEGER | DEFAULT 0 | File size in bytes |

### Indexes

- `idx_jobs_created` on `jobs(created_at DESC)`
- `idx_files_job_id` on `saved_files(job_id)`

### Connection Settings

- Journal mode: WAL (Write-Ahead Logging)
- Busy timeout: 5 seconds
- Foreign keys: enabled
- Thread safety: `check_same_thread=False` (Flask threaded mode)
- Write lock: module-level `threading.Lock` for all write operations

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key |
| `OPENROUTER_MODEL` | No | `anthropic/claude-sonnet-4-5` | Model identifier |
| `OPENROUTER_TIMEOUT` | No | `60` | API request timeout (seconds) |
| `AGENT_MAX_TOKENS` | No | `32000` | Max output tokens for document agents |
| `CHAT_MAX_TOKENS` | No | `8000` | Max output tokens for chat agent |
| `ORCHESTRATOR_MAX_TOKENS` | No | `1024` | Max output tokens for orchestrator |
| `WORKSPACE_PATH` | No | `./workspace` | Default workspace directory |
| `ALLOWED_WORKSPACE_ROOTS` | No | project root | Comma-separated allowed root paths |
| `MAX_PENDING_DOC_BYTES` | No | `204800` | Max pending document size from frontend |
| `WEB_SEARCH_TIMEOUT` | No | `15` | DuckDuckGo search timeout (seconds) |
| `GUNICORN_WORKERS` | No | `2` | Number of gevent workers |
| `GUNICORN_CONNECTIONS` | No | `50` | Max SSE connections per worker |
| `GUNICORN_TIMEOUT` | No | `120` | Worker timeout (seconds) |
| `GUNICORN_LOG_LEVEL` | No | `info` | Log level |
| `CHAT_RATE_LIMIT` | No | `10 per minute` | Per-IP rate limit for /api/chat |
| `RATELIMIT_STORAGE_URI` | No | `memory://` | Rate limiter storage backend |
| `FLASK_DEBUG` | No | `0` | Flask debug mode |
| `FLASK_HOST` | No | `0.0.0.0` | Server bind address |
| `FLASK_PORT` | No | `5000` | Server bind port |

## Running the Server

### Development

```bash
./start.sh
```

This activates the virtual environment, installs dependencies, and starts Gunicorn with gevent workers on `http://localhost:5000`.

### Direct Flask (debug only)

```bash
source venv/bin/activate
FLASK_DEBUG=1 python app.py
```

### Production

```bash
./venv/bin/gunicorn --config gunicorn.conf.py "app:app"
```

Place behind Nginx with appropriate proxy settings for SSE support.
