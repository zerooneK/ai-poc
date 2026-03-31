# Frontend Manual

## Overview

- **Framework:** Vanilla HTML/JS/CSS (no build tools, no framework)
- **Language:** JavaScript (ES6+)
- **Styling:** CSS custom properties (design tokens) with dark/light theme support
- **Markdown rendering:** marked.js (loaded from CDN)
- **Icons:** Google Material Symbols (loaded from CDN)
- **Fonts:** Inter (Latin) + Sarabun (Thai) via Google Fonts
- **SSE consumption:** Native `EventSource` API
- **HTTP client:** Native `fetch` API

The frontend consists of two self-contained HTML files: `index.html` (main chat SPA) and `history.html` (job history viewer). Both files are fully self-contained — all CSS and JavaScript is inline. No bundlers, transpilers, or package managers are used.

## Project Structure

```
ai-poc/
├── index.html          # Main SPA — chat interface, sidebar, modals (~3224 lines)
├── history.html        # Job history viewer page
└── docs/
    └── FRONTEND_MANUAL.md  # This file
```

## Layout

### index.html

The main application is a three-panel layout:

```
┌─────────────┬──────────────────────────────────────────────┐
│  Sidebar    │  Main Content                                │
│             │  ┌──────────────────────────────────────────┐ │
│  Brand      │  │  Chat Messages (scrollable)              │ │
│  New Chat   │  │  - User bubbles (right-aligned)          │ │
│  Nav Items  │  │  - Assistant bubbles (left-aligned)      │ │
│  (shortcuts)│  │  - Agent badges, PM cards, tool results  │ │
│             │  │  - Status indicators                     │ │
│  Agent      │  └──────────────────────────────────────────┘ │
│  Badges     │  ┌──────────────────────────────────────────┐ │
│             │  │  Input Bar                               │ │
│  File List  │  │  [Textarea] [Format Select] [Send]       │ │
│  (sidebar)  │  └──────────────────────────────────────────┘ │
│             │                                              │
│  Workspace  │                                              │
│  Selector   │                                              │
│  Theme      │                                              │
│  Toggle     │                                              │
└─────────────┴──────────────────────────────────────────────┘
```

### Sidebar Sections

| Section | Purpose |
|---|---|
| Brand | Project name and logo |
| New Chat | Button to start a new conversation (clears history) |
| Nav Items | Quick shortcuts that fill the input with predefined prompts |
| Agent Badges | Shows which agent handled the last request (color-coded) |
| File List | Lists files in the current workspace with size and modified date |
| Workspace Selector | Dropdown to switch between workspace folders |
| Theme Toggle | Switch between dark and light mode |

## Pages and Routes

| Route | File | Description |
|---|---|---|
| `/` | `index.html` | Main chat SPA |
| `/history` | `history.html` | Job history viewer |

## State Management

All state is managed through module-scoped JavaScript variables in the `<script>` block of `index.html`. There is no state management library.

### Global State Variables

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `pendingDoc` | string | `''` | Document content awaiting user confirmation |
| `pendingAgent` | string | `''` | Agent that created `pendingDoc` |
| `pendingFormat` | string | `'md'` | Selected output format for saving |
| `pendingTempPaths` | array | `[]` | Temp file paths from PM subtasks |
| `pendingFileAgents` | array | `[]` | Agent type per temp file (parallel array) |
| `isPendingConfirmation` | boolean | `false` | True when a document awaits save/discard |
| `wasPMTask` | boolean | `false` | True when current response is from PM flow |
| `currentPmCard` | Element | `null` | DOM element of the current PM agent card |
| `lastAgent` | string | `''` | Agent type of the most recent response |
| `queuedMessage` | string | `''` | Message queued while waiting for save confirmation |
| `pendingFileFormats` | array | `null` | Per-file format selections from PM save modal |
| `conversationHistory` | array | `[]` | `[{role, content}]` sent to backend each request |
| `userScrolledUp` | boolean | `false` | Stops auto-scroll when user scrolls up |
| `localAgentMode` | boolean | `false` | True when connected to local_agent.py on port 7000 |

### Session Management

Session IDs are stored in `localStorage` under the key `sessionId`. A new UUID is generated on first visit and reused across page reloads.

## SSE Event Handling

The frontend uses the `EventSource` API for two SSE streams:

### Chat Stream (`/api/chat`)

Consumed via `fetch` + `ReadableStream` (not `EventSource`, because POST requests cannot use `EventSource`). The response is parsed line-by-line:

```javascript
const response = await fetch('/api/chat', { method: 'POST', body: JSON.stringify(data) });
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // Parse "data: {...}" lines and dispatch by event.type
}
```

### File Stream (`/api/files/stream`)

Consumed via `EventSource` for GET-based subscription:

```javascript
const eventSource = new EventSource('/api/files/stream');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'files_changed') {
    fetch('/api/files').then(r => r.json()).then(renderFileList);
  }
};
```

## Event Types and Frontend Actions

| `type` | Frontend Action |
|---|---|
| `status` | Display message in status indicator bar |
| `agent` | Update agent badge in sidebar; create PM card if `wasPMTask` |
| `pm_plan` | Render PM plan breakdown above output area |
| `text` | Append content to live streaming output |
| `text_replace` | Replace entire output text (after fake tool-call stripping) |
| `tool_result` | Display tool result badge before output area |
| `web_search_sources` | Display source pills with clickable links |
| `pending_file` | Add temp path to `pendingTempPaths` array |
| `subtask_done` | Render Markdown for completed subtask; reset output buffer |
| `save_failed` | Show error, restore pending state |
| `error` | Display inline error message |
| `done` | Render final Markdown, re-enable send button, set pending state |
| `local_delete` | Trigger file removal from local agent file list |
| `delete_request` | Show confirmation modal for file deletion |

## Component Reference

### Chat Message Bubbles

- **User messages:** Right-aligned, dark surface background, plain text (no Markdown rendering).
- **Assistant messages:** Left-aligned, with Markdown rendering via `marked.parse()`. Includes agent badge, status indicators, and tool result badges.

### Agent Badges

Color-coded labels displayed in the sidebar and above assistant messages:

| Agent | Background | Text Color | Border |
|---|---|---|---|
| HR | `#0d2012` | `#4ade80` | `#166534` |
| Accounting | `#0d0d1f` | `#818cf8` | `#3730a3` |
| Manager | `#1a0d1a` | `#e879f9` | `#7e22ce` |
| PM | `#0d1a26` | `#38bdf8` | `#0369a1` |
| Document | `#1a1500` | `#fbbf24` | `#92400e` |
| Chat | Default surface | Default text | Default border |

### PM Cards

When the PM Agent decomposes a request, each subtask gets a colored card showing:
- Subtask number and assigned agent
- Task description
- Streaming output area
- Completion status

### Modals

| Modal | Trigger | Purpose |
|---|---|---|
| `pendingModal` | User sends a new message while a document is pending | Ask: save first, skip save, or cancel |
| `fileFormatModal` | User confirms save of PM files or single-agent document | Select output format (md/txt/docx/xlsx/pdf) per file |
| `cancelConfirmModal` | User types discard intent while PM files are pending | Confirm discarding multiple files |
| `workspaceModal` | User clicks workspace selector in sidebar | Browse and switch workspace folders |

## API Integration

All API calls use the native `fetch` API. The base URL is relative (same origin as the page).

### Key Functions

| Function | Description |
|---|---|
| `sendMessage(overrideMessage?)` | Main entry point. Handles confirmation flow interception, calls `/api/chat`, reads SSE stream, updates DOM |
| `startFileStream()` | Opens `/api/files/stream` EventSource and handles `files_changed` events |
| `renderFileList(files, workspace)` | Updates sidebar file list DOM from API response |
| `changeWorkspace()` | Opens workspace picker modal, fetches `/api/workspaces` |
| `_applyWorkspace(path)` | POSTs to `/api/workspace`, resets conversation history, restarts file stream |
| `_createWorkspaceFolder()` | POSTs to `/api/workspace/new` |

### Error Handling

- Network errors are displayed as inline error messages in the chat area.
- SSE stream errors trigger a reconnection attempt.
- Rate limit errors (429) display a Thai-language message asking the user to wait.

## Markdown Rendering

Markdown is rendered using `marked.js` (CDN):

```javascript
function _renderMarkdown(el, text) {
  const html = marked.parse(text);
  el.innerHTML = _sanitizeHtml(html);
}
```

### Sanitization

The `_sanitizeHtml()` function removes potentially dangerous content:
- `<script>` tags and their contents
- `<iframe>` tags
- `on*` event handler attributes (onclick, onerror, etc.)
- `javascript:` URLs

This is a basic sanitization layer. For production use, consider a dedicated library like DOMPurify.

## Theme System

Themes are implemented via CSS custom properties on `:root` and `body.light-mode`:

```css
:root {
  --bg: #13171f;
  --surface: #1b2130;
  --on-surface: #f0f4f8;
  --primary: #5856D6;
  /* ... more tokens */
}

body.light-mode {
  --bg: #f8f9fa;
  --surface: #eaeff1;
  --on-surface: #2b3437;
  /* ... overridden tokens */
}
```

The theme preference is stored in `localStorage` under the key `theme` and applied on page load.

## Environment Variables

The frontend has no build-time environment variables. All configuration is handled at runtime:

- The API base URL is relative (same origin), so no `API_URL` variable is needed.
- The local agent URL is hardcoded to `http://localhost:7000`.
- Theme preference is stored in `localStorage`.

## Running the Frontend

The frontend is served directly by Flask. No separate build or dev server is needed.

```bash
# Start the backend (serves the frontend automatically)
./start.sh

# Then open in browser:
# http://localhost:5000          — Main chat
# http://localhost:5000/history  — Job history
```

### Local Development

For frontend-only development (editing HTML/CSS/JS), you can open `index.html` directly in a browser. However, API calls will fail without the backend running. For a better experience, run the backend and use the browser's developer tools to inspect and modify the DOM.

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

Requires support for:
- `fetch` API
- `ReadableStream`
- `EventSource`
- CSS custom properties
- ES6+ syntax (arrow functions, async/await, template literals)

## Known Limitations

- **No client-side routing** — Both pages are served by Flask; navigation requires full page reloads.
- **Basic sanitization** — The `_sanitizeHtml()` function handles common XSS vectors but is not as comprehensive as DOMPurify.
- **No offline support** — No service worker or caching strategy. The app requires a live connection to the backend.
- **No accessibility audit** — ARIA labels and keyboard navigation have not been formally tested.
- **Single-file architecture** — All CSS and JavaScript is inline in `index.html` (~3224 lines). This makes the file large but eliminates build complexity.
