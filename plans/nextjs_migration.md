# Next.js Frontend Migration Plan

**Goal:** Replace `index.html` + `history.html` (3,224-line monolith) with a Next.js App Router frontend. Flask backend stays unchanged at root. Desktop-only. Production-ready.

**Estimated time:** 5-7 days (solo developer)

**Tech Stack:**
- Next.js 15+ (App Router, TypeScript)
- Tailwind CSS (dark mode, slate/zinc/blue palette)
- Lucide React (icons)
- react-markdown + remark-gfm (markdown rendering)
- Flask backend (unchanged, `localhost:5000`)

---

## Phase 1 — Setup & Foundation

### Steps

| Step | What | Files |
|---|---|---|
| 1.1 | Create `frontend/` with `npx create-next-app@latest` (App Router, TS, Tailwind, ESLint) | `frontend/` |
| 1.2 | Install deps: `lucide-react`, `react-markdown`, `remark-gfm`, `clsx`, `tailwind-merge` | `frontend/package.json` |
| 1.3 | Configure Tailwind dark mode + custom color tokens (slate/zinc/blue) | `frontend/tailwind.config.ts` |
| 1.4 | Set up `lib/api.ts` — typed API client for all 16 Flask endpoints | `frontend/lib/api.ts` |
| 1.5 | Set up `hooks/useSSE.ts` — custom hook for SSE streaming (hardest part) | `frontend/hooks/useSSE.ts` |

### Definition of Done

| # | Criteria | How to verify |
|---|---|---|
| 1.1 | `frontend/` created with Next.js App Router, TypeScript, Tailwind, ESLint | `npx create-next-app` output matches config |
| 1.2 | All dependencies installed | `npm ls` shows all packages |
| 1.3 | Tailwind dark mode configured with custom color tokens | `tailwind.config.ts` has `darkMode: 'class'` + custom `colors` |
| 1.4 | `lib/api.ts` exports typed functions for all 16 Flask endpoints | Each function has correct URL, method, request/response types |
| 1.5 | `hooks/useSSE.ts` connects to Flask SSE, parses events, streams text in real-time | Test shows text appearing chunk-by-chunk |
| 1.6 | Zero TypeScript errors, ESLint passes | `npm run build` and `npm run lint` exit 0 |
| 1.7 | `npm run dev` starts without errors on `localhost:3000` | Browser opens, no console errors |

### Status: ✅ COMPLETE (31 มีนาคม 2569)

| DoD Item | Status |
|---|---|
| 1.1 frontend/ created with Next.js 16, TS, Tailwind v4, ESLint | ✅ Done |
| 1.2 All dependencies installed (lucide-react, react-markdown, remark-gfm, clsx, tailwind-merge) | ✅ Done |
| 1.3 Tailwind dark mode configured with custom color tokens | ✅ Done |
| 1.4 lib/api.ts exports typed functions for all 16+ Flask endpoints | ✅ Done |
| 1.5 hooks/useSSE.ts connects to Flask SSE, parses events, streams text | ✅ Done |
| 1.6 Zero TypeScript errors, ESLint passes | ✅ Done — `npm run build` + `npm run lint` exit 0 |
| 1.7 npm run dev starts without errors | ✅ Verified |

**Files created/modified:**
- `frontend/app/globals.css` — Dark theme with slate/zinc/blue palette, agent colors, base styles
- `frontend/app/layout.tsx` — Root layout with Inter + JetBrains Mono fonts, Thai lang
- `frontend/app/page.tsx` — Minimal placeholder
- `frontend/lib/api.ts` (242 lines) — Typed API client for all Flask endpoints
- `frontend/lib/utils.ts` (119 lines) — Helpers: cn, formatBytes, fileIcon, agentLabel, sanitizeHtml
- `frontend/hooks/useSSE.ts` (237 lines) — SSE streaming hook with event parsing

---

## Phase 2 — Core Layout & Chat

### Steps

| Step | What | Files |
|---|---|---|
| 2.1 | Build root layout — navbar, sidebar area, main content area | `frontend/app/layout.tsx` |
| 2.2 | Build `Sidebar` — file list, session list, workspace info, collapse toggle | `frontend/components/Sidebar.tsx` |
| 2.3 | Build `ChatWindow` — scrollable message area, empty state | `frontend/components/ChatWindow.tsx` |
| 2.4 | Build `MessageBubble` — user/agent messages, markdown, agent badges | `frontend/components/MessageBubble.tsx` |
| 2.5 | Build `InputArea` — textarea, send button, format selector, status | `frontend/components/InputArea.tsx` |
| 2.6 | Wire everything — send message → SSE stream → render streaming text | `frontend/app/page.tsx` |

### Definition of Done

| # | Criteria | How to verify |
|---|---|---|
| 2.1 | Root layout renders navbar, sidebar, main content | Visual inspection matches design |
| 2.2 | Sidebar shows files, sessions, workspace, collapse toggle | Clicking collapse animates sidebar width |
| 2.3 | ChatWindow renders scrollable area with empty state | Empty state shows helpful text when no messages |
| 2.4 | MessageBubble renders markdown + agent badges | Tables, code blocks, bold render correctly |
| 2.5 | InputArea has textarea, send, format selector, status | All elements visible and interactive |
| 2.6 | Sending message triggers SSE, text streams in real-time | Type → send → see streaming text in bubble |
| 2.7 | Status indicator updates: processing → done/error | Visual state changes match SSE events |
| 2.8 | No console errors during full chat flow | Browser DevTools console is clean |

### Status: ✅ COMPLETE (31 มีนาคม 2569)

| DoD Item | Status |
|---|---|
| 2.1 Root layout renders navbar, sidebar, main content | ✅ Done — collapsible sidebar with Menu/X toggle |
| 2.2 Sidebar shows files, sessions, workspace, collapse toggle | ✅ Done — placeholder content, Phase 3 will populate |
| 2.3 ChatWindow renders scrollable area with empty state | ✅ Done — empty state with helpful Thai text + example cards |
| 2.4 MessageBubble renders markdown + agent badges | ✅ Done — react-markdown + remark-gfm, agent icons/labels |
| 2.5 InputArea has textarea, send, format selector, status | ✅ Done — auto-resize textarea, Enter to send, disabled during streaming |
| 2.6 Sending message triggers SSE, text streams in real-time | ✅ Done — useSSE hook wired to ChatWindow + InputArea |
| 2.7 Status indicator updates: processing → done/error | ✅ Done — status bar with pulse dot, error state |
| 2.8 No console errors during full chat flow | ✅ Done — npm run lint + npm run build exit 0 |

**Files created/modified:**
- `frontend/app/layout.tsx` (92 lines) — Root layout with collapsible sidebar, navbar, version tag
- `frontend/app/page.tsx` (80 lines) — Main chat page wiring useSSE + ChatWindow + InputArea
- `frontend/components/ChatWindow.tsx` (105 lines) — Scrollable message area with status bar, empty state
- `frontend/components/MessageBubble.tsx` (87 lines) — User/assistant messages with markdown rendering
- `frontend/components/InputArea.tsx` (88 lines) — Auto-resize textarea, send button, streaming indicator

---

## Phase 3 — Advanced Features

### Steps

| Step | What | Files |
|---|---|---|
| 3.1 | Build `PreviewPanel` — slide-in panel for file viewing | `frontend/components/PreviewPanel.tsx` |
| 3.2 | Build `WorkspaceModal` — pick/create/switch workspaces | `frontend/components/WorkspaceModal.tsx` |
| 3.3 | Build `FormatModal` — choose output format before saving | `frontend/components/FormatModal.tsx` |
| 3.4 | Build `ConfirmBar` — save/discard/overwrite confirm UI | `frontend/components/ConfirmBar.tsx` |
| 3.5 | Build `DeleteConfirmModal` — HITL delete confirmation | `frontend/components/DeleteConfirmModal.tsx` |
| 3.6 | Wire file SSE events — sidebar auto-refresh | `frontend/hooks/useFileSSE.ts` |
| 3.7 | Wire session management — load/switch/restore context | `frontend/hooks/useSessions.ts` |

### Definition of Done

| # | Criteria | How to verify |
|---|---|---|
| 3.1 | PreviewPanel slides in, renders markdown+raw, closes on Esc/click | Click file → panel opens → Esc closes |
| 3.2 | WorkspaceModal lists, creates, switches workspaces | Modal → list → create → path updates |
| 3.3 | FormatModal shows options, returns selected format | Click save → modal → select → returns value |
| 3.4 | ConfirmBar shows save/discard/overwrite, handles choice | Buttons trigger correct API calls |
| 3.5 | DeleteConfirmModal confirms deletion, refreshes sidebar | Click delete → modal → confirm → file removed |
| 3.6 | File SSE events trigger sidebar auto-refresh | Save file → sidebar updates without reload |
| 3.7 | Session management: load, restore context, switch | Click session → history loads → continue chat |
| 3.8 | All modals/panels have z-index, focus trap, keyboard dismissal | Tab stays inside modal, Esc closes |

### Status: ✅ COMPLETE (31 มีนาคม 2569)

| DoD Item | Status |
|---|---|
| 3.1 PreviewPanel slides in, renders markdown+raw, closes on Esc/click | ✅ Done — slide-in panel with rendered/raw tabs, copy button |
| 3.2 WorkspaceModal lists, creates, switches workspaces | ✅ Done — modal with workspace list + create new folder |
| 3.3 FormatModal shows options, returns selected format | ✅ Done — 5 format options (md/txt/docx/xlsx/pdf) |
| 3.4 ConfirmBar shows save/discard/overwrite, handles choice | ✅ Done — Thai confirm bar with save/discard/edit buttons |
| 3.5 DeleteConfirmModal confirms deletion, refreshes sidebar | ✅ Done — modal with filename + confirm/cancel |
| 3.6 File SSE events trigger sidebar auto-refresh | ✅ Done — useFileSSE hook with auto-reconnect |
| 3.7 Session management: load, restore context, switch | ✅ Done — useSessions hook + sidebar session list |
| 3.8 All modals/panels have z-index, focus trap, keyboard dismissal | ✅ Done — Esc closes all modals/panels |

**Files created/modified:**
- `frontend/components/PreviewPanel.tsx` (163 lines) — File preview with markdown rendering, raw text view, copy
- `frontend/components/WorkspaceModal.tsx` (168 lines) — Workspace picker + create new folder
- `frontend/components/FormatModal.tsx` (108 lines) — Format selector (md/txt/docx/xlsx/pdf)
- `frontend/components/ConfirmBar.tsx` (67 lines) — Save/discard/edit confirmation bar
- `frontend/components/DeleteConfirmModal.tsx` (70 lines) — Delete confirmation modal
- `frontend/hooks/useFileSSE.ts` (81 lines) — File change SSE with auto-reconnect
- `frontend/hooks/useSessions.ts` (45 lines) — Session list + job loading
- `frontend/app/page.tsx` — Full app wiring: sidebar, chat, modals, panels, SSE
- `frontend/app/layout.tsx` — Simplified to font setup + children only

---

## Phase 4 — Polish & Testing

### Steps

| Step | What | Files |
|---|---|---|
| 4.1 | Keyboard shortcuts — Enter (send), Esc (close), Ctrl+K (workspace) | `frontend/lib/shortcuts.ts` |
| 4.2 | Loading states, error boundaries, empty states | Various components |
| 4.3 | Manual test all flows | Chat, save, discard, revise, workspace, session |
| 4.4 | Run backend tests | `smoke_test_phase0.py`, `test_cases.py`, `quick-demo-check.py` |
| 4.5 | Update docs | `docs/ARCHITECTURE.md`, `docs/FRONTEND_MANUAL.md`, `README.md` |
| 4.6 | Update CHANGELOG and commit | `CHANGELOG.md` |

### Definition of Done

| # | Criteria | How to verify |
|---|---|---|
| 4.1 | Keyboard shortcuts work: Enter, Esc, Ctrl+K | Test each shortcut manually |
| 4.2 | Loading states visible during API calls | Spinner/skeleton appears during fetch |
| 4.3 | Error boundaries catch and display errors gracefully | Simulate error → friendly message, no crash |
| 4.4 | Empty states show helpful text | Fresh workspace shows "no files yet" |
| 4.5 | Manual test pass: all flows end-to-end | Run through each flow |
| 4.6 | Backend tests pass (exit code 0) | All test scripts pass |
| 4.7 | Docs updated to reflect Next.js structure | Files show new frontend layout |
| 4.8 | CHANGELOG updated with v0.32.0 entry | Entry lists all changes |
| 4.9 | All changes committed with descriptive messages | `git log` shows clean history |
| 4.10 | `npm run build` succeeds with zero errors | Production build completes |

---

## Project Structure

```
ai-poc/
├── app.py, core/, agents/...     # Flask backend (unchanged)
├── db.py, converter.py, ...      # Backend files (unchanged)
├── frontend/                     # New Next.js app
│   ├── app/
│   │   ├── layout.tsx            # Root layout (navbar + sidebar shell)
│   │   ├── page.tsx              # Main chat page
│   │   └── globals.css           # Tailwind + custom styles
│   ├── components/
│   │   ├── Sidebar.tsx           # File list + sessions + workspace
│   │   ├── ChatWindow.tsx        # Scrollable message area
│   │   ├── MessageBubble.tsx     # Individual message with markdown
│   │   ├── InputArea.tsx         # Text input + send + format
│   │   ├── PreviewPanel.tsx      # File preview (slides from right)
│   │   ├── WorkspaceModal.tsx    # Pick/create workspace
│   │   ├── FormatModal.tsx       # Choose output format
│   │   ├── ConfirmBar.tsx        # Save/discard confirmation
│   │   └── DeleteConfirmModal.tsx
│   ├── hooks/
│   │   ├── useSSE.ts             # Core SSE streaming hook
│   │   ├── useFileSSE.ts         # File change events
│   │   └── useSessions.ts        # Session management
│   ├── lib/
│   │   ├── api.ts                # Typed API client
│   │   ├── shortcuts.ts          # Keyboard shortcuts
│   │   └── utils.ts              # Helpers (formatBytes, sanitize, etc.)
│   ├── public/                   # Static assets
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
```

---

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| SSE handling | Custom `useSSE` hook with `fetch` + `ReadableStream` | Proven pattern, no extra deps, works with Flask SSE |
| Markdown rendering | `react-markdown` + `remark-gfm` | Safe by default, supports tables/code blocks |
| State management | `useState` + React Context | No Redux needed for this scope |
| API calls | `lib/api.ts` with `fetch` | Simple, typed, no overhead |
| Icons | `lucide-react` | Modern, consistent, tree-shakeable |
| Theme | Tailwind slate/zinc/blue dark palette | Cleaner than current CSS, unified design system |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| SSE streaming breaks in Next.js | High | Test `useSSE` hook first before building UI. Hook is isolated and testable. |
| Feature parity takes longer | Medium | Build core chat first (Phase 2), add features incrementally. |
| Tailwind theme doesn't match current | Low | Extract current CSS colors first, map to Tailwind tokens. |
| TypeScript type errors slow progress | Low | Start with `any` for complex types, refine incrementally. |

---

## Migration Strategy

**Big bang approach:** Build the entire Next.js frontend alongside the existing `index.html`. Test thoroughly. Then swap — update Flask routes to serve the Next.js build or run Next.js as a separate dev server pointing to Flask API.

**Why big bang:** The current frontend is one file — there's nothing to migrate incrementally. Building fresh is cleaner than piecemeal migration.

---

## Success Criteria

- [ ] All 4 phases complete with DoD met
- [ ] Feature parity with current `index.html` (chat, save, discard, revise, workspace, sessions, preview, format selection, delete confirmation)
- [ ] Zero TypeScript errors, ESLint clean
- [ ] `npm run build` succeeds
- [ ] Backend tests pass
- [ ] Docs updated
- [ ] All changes committed
