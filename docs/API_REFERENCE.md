# API Reference — AI Assistant Internal POC

> **Version:** v0.31.0 | **Base URL:** `http://localhost:5000`
>
> All endpoints return JSON unless the response body is a file download or an SSE stream.
> All SSE endpoints return `Content-Type: text/event-stream; charset=utf-8`.
> Error responses always include `{"error": "<message>"}`.

---

## Table of Contents

- [POST /api/chat](#post-apichat)
- [GET /api/health](#get-apihealth)
- [GET /api/history](#get-apihistory)
- [GET /api/history/\<job\_id\>](#get-apihistoryjob_id)
- [GET /api/files](#get-apifiles)
- [GET /api/files/stream](#get-apifilesstream)
- [GET /api/preview](#get-apipreview)
- [GET /api/serve/\<filename\>](#get-apiservefilename)
- [POST /api/delete](#post-apidelete)
- [GET /api/workspace](#get-apiworkspace)
- [POST /api/workspace](#post-apiworkspace)
- [GET /api/workspaces](#get-apiworkspaces)
- [POST /api/workspace/new](#post-apiworkspacenew)
- [GET /api/sessions](#get-apisessions)
- [GET /api/sessions/\<session\_id\>](#get-apisessionssession_id)
- [DELETE /api/sessions/\<session\_id\>](#delete-apisessionssession_id)
- [SSE Event Schema Reference](#sse-event-schema-reference)

---

## POST /api/chat

The primary endpoint. Accepts a user message and streams the AI response as Server-Sent Events.

**Rate limit:** 10 requests per minute per IP address.

**Auth required:** No.

### Request

```
Content-Type: application/json
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | The user's message or instruction. Must be non-empty after stripping whitespace. |
| `session_id` | string | No | Session identifier, `8–64` alphanumeric chars and hyphens (`^[\w\-]{8,64}$`). Scopes the workspace and job history for this browser tab. |
| `pending_doc` | string | No | The full Markdown text of the current pending document (held by browser). Truncated server-side to `MAX_PENDING_DOC_BYTES` (default 200 KB). |
| `pending_agent` | string | No | Agent key string for the pending document (`hr`, `accounting`, `manager`, `document`, `chat`). |
| `pending_temp_paths` | string[] | No | Array of `temp/` file paths from a PM Agent run that are staged and awaiting save confirmation. Each path is validated server-side. |
| `agent_types` | string[] | No | Parallel array to `pending_temp_paths` indicating the agent type for each staged file. Used when saving to set `saved_files.agent`. |
| `output_format` | string | No | Export format for new files: `md` (default), `txt`, `docx`, `xlsx`, `pdf`. |
| `output_formats` | string[] | No | Per-file format overrides parallel to `pending_temp_paths` for PM multi-save. |
| `overwrite_filename` | string | No | If set, saves the pending document over an existing workspace file instead of creating a new one. Must match `^[\w.\-]{1,120}$`. |
| `local_agent_mode` | boolean | No | When `true`, replaces the default `READ_ONLY_TOOLS` with `LOCAL_AGENT_TOOLS` (`web_search` + `local_delete` only — no workspace writes). Default `false`. |
| `conversation_history` | array | No | Array of `{role: "user"|"assistant", content: string}` objects. Last 20 entries are used. Each content string is truncated to 3000 characters. |

### Response

`HTTP 200 OK` with `Content-Type: text/event-stream; charset=utf-8`.

The body is a stream of SSE frames. Each frame:

```
data: <JSON object>\n\n
```

The stream always terminates with a `{"type":"done"}` frame. See the [SSE Event Schema Reference](#sse-event-schema-reference) for all event types.

### Error Responses

| Status | Condition |
|---|---|
| `400` | Request body is not JSON, `message` is empty, or `session_id` is present but invalid |
| `429` | Rate limit exceeded |

### Examples

**Simple document request:**

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "ทำสัญญาจ้างพนักงาน นายสมชาย ใจดี ตำแหน่ง Software Engineer เงินเดือน 80,000 บาท เริ่มงาน 1 พฤษภาคม 2569",
    "session_id": "session-abc-12345678",
    "output_format": "docx"
  }'
```

**Save the pending document:**

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "บันทึก",
    "session_id": "session-abc-12345678",
    "pending_doc": "# สัญญาจ้างงาน\n\nเนื้อหาสัญญา...",
    "pending_agent": "hr",
    "output_format": "docx"
  }'
```

**Edit the pending document:**

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "แก้ไขเงินเดือนเป็น 90,000 บาท",
    "session_id": "session-abc-12345678",
    "pending_doc": "# สัญญาจ้างงาน\n\nเงินเดือน 80,000 บาท...",
    "pending_agent": "hr"
  }'
```

**Confirm a PM multi-document save:**

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "บันทึก",
    "session_id": "session-abc-12345678",
    "pending_temp_paths": ["/path/to/temp/hr_contract_20260402.md", "/path/to/temp/accounting_invoice_20260402.md"],
    "agent_types": ["hr", "accounting"],
    "output_format": "md"
  }'
```

---

## GET /api/health

Returns the current server health status, active model, and workspace path.

**Auth required:** No.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | No | If provided and invalid, returns 400 instead of using the global workspace. |

### Response

`HTTP 200 OK`

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

### Error Responses

| Status | Condition |
|---|---|
| `400` | `session_id` provided but fails validation regex |

### Example

```bash
curl http://localhost:5000/api/health
```

---

## GET /api/history

Returns a paginated list of recent jobs with their associated saved files.

**Auth required:** No.

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | `50` | Number of jobs to return. Clamped to range `[1, 200]`. |

### Response

`HTTP 200 OK`

```json
{
  "jobs": [
    {
      "id": "3f2a1b4c-...",
      "created_at": "2026-04-02T08:30:00.000000+00:00",
      "session_id": "session-abc-12345678",
      "user_input": "ทำสัญญาจ้าง...",
      "agent": "hr",
      "reason": "งานเกี่ยวกับเอกสาร HR",
      "status": "completed",
      "output_text": "# สัญญาจ้างงาน...",
      "files": [
        {
          "job_id": "3f2a1b4c-...",
          "filename": "hr_contract_20260402_083000.docx",
          "agent": "hr",
          "size_bytes": 18432,
          "created_at": "2026-04-02T08:30:45.000000+00:00"
        }
      ]
    }
  ],
  "db_available": true
}
```

**Job `status` values:** `pending`, `completed`, `error`, `discarded`.

### Example

```bash
curl "http://localhost:5000/api/history?limit=20"
```

---

## GET /api/history/\<job_id\>

Returns the full record for a single job by its UUID.

**Auth required:** No.

### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | UUID v4 of the job. |

### Response

`HTTP 200 OK` — same shape as a single element of the `jobs` array from `GET /api/history`.

### Error Responses

| Status | Condition |
|---|---|
| `404` | Job ID not found in the database |

### Example

```bash
curl http://localhost:5000/api/history/3f2a1b4c-8e5d-4f2a-9b1c-7d6e5f4a3b2c
```

---

## GET /api/files

Lists all files in the current workspace (or the session-scoped workspace if `session_id` is provided).

**Auth required:** No.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | No | If provided, resolves the session-scoped workspace. |

### Response

`HTTP 200 OK`

```json
{
  "files": [
    {
      "name": "hr_contract_somchai_20260402_083000.docx",
      "size": 18432,
      "modified": "2026-04-02 08:30"
    },
    {
      "name": "invoice_001_20260401.md",
      "size": 2048,
      "modified": "2026-04-01 15:22"
    }
  ]
}
```

Files are sorted alphabetically by name. The `modified` field uses `Asia/Bangkok` local time formatted as `YYYY-MM-DD HH:MM`.

### Error Responses

| Status | Condition |
|---|---|
| `400` | `session_id` provided but invalid |

### Example

```bash
curl "http://localhost:5000/api/files?session_id=session-abc-12345678"
```

---

## GET /api/files/stream

Long-lived SSE endpoint. The browser subscribes to this endpoint to receive real-time workspace change notifications. Used to update the file sidebar without polling.

**Auth required:** No.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | No | Scopes the change notifications to the session's workspace. |

### Response

`HTTP 200 OK` with `Content-Type: text/event-stream; charset=utf-8`.

Emits two event types:

| Event | Payload | Interval |
|---|---|---|
| `files_changed` | `{}` | Whenever any file is created, updated, or deleted in the watched workspace |
| `heartbeat` | `{}` | Every 30 seconds when no changes have occurred, to keep the connection alive |

The connection stays open indefinitely. The browser should reconnect on error using the `EventSource` API's built-in reconnect behavior.

### Example

```javascript
const es = new EventSource('/api/files/stream?session_id=session-abc-12345678');
es.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'files_changed') fetchFileList();
};
```

---

## GET /api/preview

Returns the text content of a file in the workspace. Supports `.md`, `.txt`, `.docx`, `.xlsx`, and `.pdf` (text extraction).

**Auth required:** No.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file` | string | Yes | Filename (no path). Must match `^[\w.\-]{1,200}$`. |
| `session_id` | string | No | Session-scoped workspace lookup. |

### Response

`HTTP 200 OK`

```json
{
  "filename": "hr_contract_somchai.md",
  "content": "# สัญญาจ้างงาน\n\n...",
  "ext": ".md",
  "size": 2048
}
```

For binary formats (`.docx`, `.xlsx`, `.pdf`), `content` is the extracted plain text. Text files are returned as-is (capped at 80,000 characters).

### Error Responses

| Status | Condition |
|---|---|
| `400` | Missing or invalid `file` parameter, or invalid `session_id` |
| `403` | Resolved path is outside the workspace directory (path traversal attempt) |
| `404` | File not found |
| `500` | Text extraction failed |

### Example

```bash
curl "http://localhost:5000/api/preview?file=hr_contract_somchai.md&session_id=session-abc-12345678"
```

---

## GET /api/serve/\<filename\>

Serves raw file bytes from the workspace. Used for inline PDF preview in the browser (`<iframe src="/api/serve/doc.pdf">`).

**Auth required:** No.

**Caching:** `max-age=60` seconds (conditional GET with ETag support).

### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `filename` | string | Filename (no path). Must match `^[\w.\-]{1,200}$`. |

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | No | Session-scoped workspace lookup. |

### Response

`HTTP 200 OK` with the appropriate `Content-Type` for the file extension. Body is raw file bytes.

### Error Responses

| Status | Condition |
|---|---|
| `400` | Invalid `filename` or invalid `session_id` |
| `403` | Path resolves outside the workspace |
| `404` | File not found |

### Example

```bash
curl http://localhost:5000/api/serve/invoice_001.pdf -o invoice_preview.pdf
```

---

## POST /api/delete

Deletes a file from the workspace.

**Rate limit:** 20 requests per minute per IP address.

**Auth required:** No.

### Request

```
Content-Type: application/json
```

| Field | Type | Required | Description |
|---|---|---|---|
| `filename` | string | Yes | Filename to delete. Must match `^[\w.\-]{1,120}$`. |
| `session_id` | string | No | Session-scoped workspace. If present and invalid, returns 400. |

### Response

`HTTP 200 OK`

```json
{
  "success": true,
  "filename": "hr_contract_somchai.md"
}
```

### Error Responses

| Status | Condition |
|---|---|
| `400` | Missing or invalid `filename`, or invalid `session_id` |
| `400` | File not found, or other filesystem error (error message returned in `error` field) |

### Example

```bash
curl -X POST http://localhost:5000/api/delete \
  -H "Content-Type: application/json" \
  -d '{"filename": "hr_contract_somchai.md", "session_id": "session-abc-12345678"}'
```

---

## GET /api/workspace

Returns the current active workspace path for this session (or the global workspace if no session).

**Auth required:** No.

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | No | If provided, returns the session-scoped workspace path. |

### Response

`HTTP 200 OK`

```json
{
  "workspace": "/home/user/ai-poc/workspace"
}
```

### Error Responses

| Status | Condition |
|---|---|
| `400` | `session_id` provided but fails validation |

### Example

```bash
curl "http://localhost:5000/api/workspace?session_id=session-abc-12345678"
```

---

## POST /api/workspace

Sets the active workspace path. The new path must be within one of the configured `ALLOWED_WORKSPACE_ROOTS`. The directory is created if it does not exist.

**Auth required:** No.

### Request

```
Content-Type: application/json
```

| Field | Type | Required | Description |
|---|---|---|---|
| `path` | string | Yes | Absolute or relative path to the workspace directory. |
| `session_id` | string | No | If provided, scopes the change to this session only. Without `session_id`, the global workspace is updated (and a warning is logged). |

### Response

`HTTP 200 OK`

```json
{
  "workspace": "/home/user/ai-poc/workspace"
}
```

The `workspace` field contains the resolved absolute path.

### Error Responses

| Status | Condition |
|---|---|
| `400` | Request is not JSON, `path` is empty, resolved path is outside `ALLOWED_WORKSPACE_ROOTS`, or invalid `session_id` |

### Example

```bash
curl -X POST http://localhost:5000/api/workspace \
  -H "Content-Type: application/json" \
  -d '{"path": "./workspace/project-alpha", "session_id": "session-abc-12345678"}'
```

---

## GET /api/workspaces

Lists all available workspace subdirectories under the configured `ALLOWED_WORKSPACE_ROOTS`. Used to populate the workspace switcher UI.

**Auth required:** No.

### Response

`HTTP 200 OK`

```json
{
  "workspaces": [
    {
      "name": "workspace",
      "path": "/home/user/ai-poc/workspace"
    },
    {
      "name": "project-alpha",
      "path": "/home/user/ai-poc/project-alpha"
    }
  ]
}
```

Entries are sorted alphabetically by name. Only direct subdirectories of allowed roots are listed — not the roots themselves.

### Example

```bash
curl http://localhost:5000/api/workspaces
```

---

## POST /api/workspace/new

Creates a new workspace subdirectory and sets it as the active workspace for the session.

**Auth required:** No.

### Request

```
Content-Type: application/json
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Directory name. Must match `^[\w]{1,60}$` (letters, digits, underscore only — no spaces or hyphens). |
| `session_id` | string | No | If provided, scopes the new workspace to this session. |

### Response

`HTTP 201 Created`

```json
{
  "workspace": "/home/user/ai-poc/workspace_new"
}
```

The new directory is created under the same parent as `WORKSPACE_PATH`.

### Error Responses

| Status | Condition |
|---|---|
| `400` | Request is not JSON, `name` fails the `^[\w]{1,60}$` pattern, or the resolved path is outside `ALLOWED_WORKSPACE_ROOTS`, or invalid `session_id` |

### Example

```bash
curl -X POST http://localhost:5000/api/workspace/new \
  -H "Content-Type: application/json" \
  -d '{"name": "project_q2_2569", "session_id": "session-abc-12345678"}'
```

---

## GET /api/sessions

Lists all sessions ordered by most recent activity.

**Auth required:** No.

### Response

`HTTP 200 OK`

```json
{
  "sessions": [
    {
      "session_id": "session-abc-12345678",
      "first_message": "ทำสัญญาจ้าง...",
      "last_active": "2026-04-02T09:15:00.000000+00:00",
      "created_at": "2026-04-02T08:00:00.000000+00:00",
      "job_count": 12,
      "last_agent": "hr"
    }
  ]
}
```

Returns at most 20 sessions. Returns `{"sessions": []}` when the database is unavailable.

### Example

```bash
curl http://localhost:5000/api/sessions
```

---

## GET /api/sessions/\<session_id\>

Returns all completed jobs for a session, ordered oldest-first.

**Auth required:** No.

### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier. Must match `^[\w\-]{8,64}$`. |

### Response

`HTTP 200 OK`

```json
{
  "jobs": [
    {
      "id": "3f2a1b4c-...",
      "created_at": "2026-04-02T08:30:00.000000+00:00",
      "user_input": "ทำสัญญาจ้าง...",
      "agent": "hr",
      "output_text": "# สัญญาจ้างงาน..."
    }
  ]
}
```

Only jobs with `status = 'completed'` are included.

### Error Responses

| Status | Condition |
|---|---|
| `400` | `session_id` fails validation |

### Example

```bash
curl http://localhost:5000/api/sessions/session-abc-12345678
```

---

## DELETE /api/sessions/\<session_id\>

Deletes all job and file records for a session from the database and clears the session workspace mapping from memory.

**Note:** This does not delete any files on disk — it only removes database records and the in-memory workspace mapping.

**Auth required:** No.

### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier. Must match `^[\w\-]{8,64}$`. |

### Response

`HTTP 200 OK`

```json
{
  "success": true,
  "session_id": "session-abc-12345678"
}
```

### Error Responses

| Status | Condition |
|---|---|
| `400` | `session_id` fails validation |
| `404` | No jobs found for this session in the database |

### Example

```bash
curl -X DELETE http://localhost:5000/api/sessions/session-abc-12345678
```

---

## SSE Event Schema Reference

All events on the `/api/chat` stream are JSON objects with a `type` field. The browser reads them via `EventSource.onmessage`.

### `status`

Informational progress update. The browser should display this as a non-permanent status indicator.

```json
{"type": "status", "message": "กำลังวิเคราะห์งาน..."}
```

### `agent`

Announces which agent was selected by the Orchestrator, or which sub-agent is starting within a PM subtask.

```json
{"type": "agent", "agent": "hr", "reason": "งานเกี่ยวกับสัญญาจ้างงาน"}
```

```json
{"type": "agent", "agent": "accounting", "reason": "Subtask 2/2", "task": "ออก Invoice สำหรับลูกค้า ABC"}
```

The optional `task` field is present only during PM subtask execution and contains the first 80 characters of the subtask description.

### `text`

A streamed chunk of the AI response. Chunks arrive in order and should be concatenated by the browser. The full concatenated text becomes `pendingDoc` when `done` is received.

```json
{"type": "text", "content": "รับทราบครับ จะจัดทำสัญญาจ้างให้เลยนะครับ\n\n## สัญญาจ้างงาน\n\n"}
```

### `text_replace`

Replaces the entire accumulated text buffer. Emitted after the server strips fake tool-call JSON from the streamed content. The browser should discard all previously received `text` chunks and use this value instead.

```json
{"type": "text_replace", "content": "รับทราบครับ จะจัดทำสัญญาจ้างให้เลยนะครับ\n\n## สัญญาจ้างงาน\n\n"}
```

### `tool_result`

Result of a tool call executed by the agent. The browser displays this inline in the chat as a collapsible status badge.

```json
{"type": "tool_result", "tool": "create_file", "result": "✅ สร้างไฟล์ 'hr_contract.md' สำเร็จ (1420 ตัวอักษร)"}
```

```json
{"type": "tool_result", "tool": "read_file", "result": "# สัญญาจ้างงาน\n\n...", "filename": "hr_contract.md"}
```

Result strings longer than 500 characters are truncated with `…` in this event (the full string is used internally).

### `web_search_sources`

Source URLs extracted from a `web_search` tool result. Used by the browser to display citation badges below AI-generated content that references online sources.

```json
{
  "type": "web_search_sources",
  "query": "อัตราค่าแรงขั้นต่ำไทย 2569",
  "sources": [
    {"url": "https://www.mol.go.th/...", "domain": "www.mol.go.th"},
    {"url": "https://www.boi.go.th/...", "domain": "www.boi.go.th"}
  ]
}
```

### `pm_plan`

Emitted after PM Agent completes planning, before subtask execution begins. The browser uses this to render a subtask progress list.

```json
{
  "type": "pm_plan",
  "subtasks": [
    {"agent": "hr", "task": "จัดทำสัญญาจ้างงานสำหรับนายสมชาย ใจดี ตำแหน่ง SE เงินเดือน 80,000 บาท"},
    {"agent": "accounting", "task": "ออก Invoice สำหรับค่าบริการที่ปรึกษาเดือนเมษายน 2569"}
  ]
}
```

### `pending_file`

Emitted after a PM subtask completes and a draft file is written to `temp/`. The browser should add `temp_path` to its `pendingTempPaths` array.

```json
{
  "type": "pending_file",
  "temp_path": "/home/user/ai-poc/temp/hr_contract_somchai_20260402_083045.md",
  "filename": "hr_contract_somchai_20260402_083045.md",
  "agent": "hr"
}
```

### `subtask_done`

Emitted at the end of each PM subtask (whether successful or not). The browser uses `index` and `total` to update a progress indicator.

```json
{"type": "subtask_done", "agent": "hr", "index": 0, "total": 2}
```

### `delete_request`

The agent called `request_delete` to ask for user confirmation before deleting a file. The browser must display a confirmation dialog. If confirmed, the browser sends `POST /api/delete`.

```json
{"type": "delete_request", "filename": "hr_contract_old.md"}
```

### `local_delete`

Used in Local Agent Mode only. The agent called `local_delete`. The browser should delete the named file from the user's local machine (via a local file system API).

```json
{"type": "local_delete", "filename": "draft_report.md"}
```

### `save_failed`

A file save operation failed. The `pendingDoc` state should be preserved in the browser so the user can retry.

```json
{"type": "save_failed", "message": "ไม่สามารถบันทึกไฟล์ได้ กรุณาลองใหม่อีกครั้ง"}
```

### `error`

An unrecoverable error occurred. The stream may continue after this event (e.g., the `done` event still follows).

```json
{"type": "error", "message": "เกิดข้อผิดพลาดจากระบบ กรุณาลองใหม่อีกครั้ง"}
```

### `done`

The stream is complete. The browser finalises `pendingDoc` from the accumulated `text` events, resets the input UI, and re-enables controls.

```json
{"type": "done"}
```

### `files_changed` (files/stream only)

Emitted on `/api/files/stream` when any file in the watched workspace is created, updated, or deleted.

```json
{"type": "files_changed"}
```

### `heartbeat` (files/stream only)

Emitted on `/api/files/stream` every 30 seconds when no changes have occurred. Keeps the `EventSource` connection alive through proxies and load balancers that time out idle connections.

```json
{"type": "heartbeat"}
```
