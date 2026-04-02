# Changelog — Internal AI Assistant POC

## [v0.32.11] — 2 เมษายน 2569 · feat
- feat (frontend/app/page.tsx): เพิ่ม sidebar แบบพับ/ขยายได้ใน Next.js frontend โดยยังคงใช้งาน workspace, file list, session list และลบ session ได้ในโหมดย่อ
- fix (frontend/app/page.tsx): ย้ายปุ่มพับ/ขยายเข้าไปไว้ใน sidebar และย้ายตัวเลือก workspace ไปไว้ด้านล่างของ sidebar ตาม layout ใหม่
- fix (frontend/app/page.tsx): ปรับโหมด sidebar แบบย่อให้เป็น compact rail ที่อ่านง่ายขึ้น ลดความรกจากตัวเลข/ปุ่มซ้อนกัน
- fix (frontend/app/page.tsx): รีโหลดหน้าใน Next.js frontend จะเริ่ม session ใหม่ทุกครั้ง ป้องกันการเลือก session เก่าค้างแต่หน้าจอเปิดเป็นแชทใหม่

## [v0.32.10] — 2 เมษายน 2569 · fix
- fix (agents/pm_agent.py): ครอบ PM planning API call ด้วย `try/except` แล้ว fallback เป็น `[]` เมื่อ upstream error แทนการ throw
- fix (app.py): `/api/preview` ใช้ path traversal guard แบบเดียวกับ `/api/serve` แล้ว ปิดช่อง `startswith(workspace)` ที่ขาด `os.sep`
- fix (app.py): validate `output_formats` รายไฟล์ด้วย whitelist เดียวกับ `output_format` ป้องกัน extension ที่ไม่อนุญาต
- fix (app.py): PM path ที่ `plan()` คืนค่าว่างจะส่ง SSE `done` ก่อน `return` แล้ว ป้องกัน frontend ค้าง loading
- fix (app.py): ลบการ mark job เป็น `discarded` ผิดกรณีตอนผู้ใช้พิมพ์คำสั่งแก้ไขขณะยังมีไฟล์ PM รอบันทึก
- fix (agents/base_agent.py): กัน truncated tool-call args เมื่อ `finish_reason='length'` โดยส่ง `error` และหยุด loop ก่อน parse JSON ที่ไม่ครบ

## [v0.32.9] — 1 เมษายน 2569 · fix
- fix (frontend/): กด session ใน sidebar แล้วโหลดบทสนทนาทั้งหมดของ session นั้นกลับมาแสดงในหน้าจอ
- fix (frontend/): เปลี่ยน active session ของหน้าให้ตรงกับ session ที่ผู้ใช้เลือก เพื่อให้ chat, file list, และ workspace state อยู่ในบริบทเดียวกัน

## [v0.32.8] — 1 เมษายน 2569 · fix
- fix (frontend/): ล้าง status bar เมื่อ SSE stream จบ, abort, หรือ error แล้ว ป้องกันข้อความค้างเช่น "กำลังตรวจสอบ workspace..."
- fix (frontend/): ลบการ render ที่ผิดกติกาใน `MessageBubble` ซึ่งเคยส่งทั้ง `dangerouslySetInnerHTML` และ `children` พร้อมกัน

## [v0.32.7] — 1 เมษายน 2569 · fix
- fix (app.py): ทำให้ทุก route ที่แตะ workspace ใช้ session workspace เดียวกันกับ `chat()` แล้ว
  - `GET /api/health`, `GET /api/files`, `GET /api/files/stream`, `GET /api/preview`, `GET /api/serve/<filename>`, `POST /api/delete`, `GET /api/workspace`, `POST /api/workspace`, `POST /api/workspace/new`
  - ถ้าส่ง `session_id` ไม่ถูกต้อง จะตอบ `400 invalid session_id` แทนการ fallback ไป global workspace
- fix (frontend/): ส่ง `session_id` ไปทุก workspace/file API ใน Next.js frontend
  - สร้าง session id คงที่ใน browser
  - file SSE, preview, delete, workspace switch/create ใช้ session scope เดียวกัน
- fix (frontend/): แก้ duplicate assistant message จาก `useSSE` เรียก completion callback ซ้ำ 2 รอบ
- fix (frontend/): ย้าย network side effects ออกจาก render path ใน `WorkspaceModal` และ `PreviewPanel`
- fix (local_agent.py): ทำให้ `update` ล้มเหลวเมื่อไฟล์ยังไม่มีอยู่จริง ให้ behavior ตรงกับ `mcp_server.py`
- test (smoke_test_phase0.py): เอา path แบบ Windows-only ออก ใช้ path ใต้ repo แทน
- test (test_workspace_isolation.py): เพิ่ม integration test สำหรับ session-scoped workspace/file APIs

## [v0.32.6] — 31 มีนาคม 2569 · fix
- fix (frontend/): แก้ UI layout ไม่เต็มจอ — เปลี่ยน root div จาก `h-screen` → `h-full` ให้ inherit จาก body `h-screen` ป้องกัน overflow
  - html/body มี `height: 100vh` ชัดเจน
  - body มี `h-screen overflow-hidden`
  - Sidebar, ChatWindow, InputArea ใช้ flex layout ถูกต้อง

## [v0.32.5] — 31 มีนาคม 2569 · feat
- feat (start.sh): รันทั้ง Flask backend (port 5000) และ Next.js frontend (port 3000) ด้วยคำสั่งเดียว
  - Ctrl+C หยุดเซิร์ฟเวอร์ทั้งหมดพร้อมกัน
  - ตรวจสอบ .env, venv, dependencies ทั้ง backend และ frontend
  - ถ้าไม่มี frontend/ จะรันเฉพาะ backend

## [v0.32.4] — 31 มีนาคม 2569 · feat
- feat (frontend/): Phase 4 Polish & Testing — เสร็จสมบูรณ์ ✅
  - Keyboard shortcuts: Enter (send), Esc (close panel), Ctrl/Cmd+K (workspace)
  - ErrorBoundary: class component with Thai error UI + retry button
  - LoadingSpinner: animated spinner component
  - Empty states: helpful Thai text + example cards in ChatWindow
  - npm run build + npm run lint ผ่านทั้งหมด (0 errors, 0 warnings)

## [v0.32.3] — 31 มีนาคม 2569 · feat
- feat (frontend/): Phase 3 Advanced Features — เสร็จสมบูรณ์ ✅
  - PreviewPanel: slide-in panel, markdown/raw tabs, copy button, Esc to close
  - WorkspaceModal: list workspaces, create new folder, switch workspace
  - FormatModal: 5 format options (md/txt/docx/xlsx/pdf)
  - ConfirmBar: save/discard/edit confirmation with Thai text
  - DeleteConfirmModal: HITL delete confirmation
  - useFileSSE hook: file change events with auto-reconnect
  - useSessions hook: session list + job loading
  - Full sidebar: file list with icons/sizes, session list with agent badges
  - npm run build + npm run lint ผ่านทั้งหมด (0 errors, 0 warnings)

## [v0.32.2] — 31 มีนาคม 2569 · feat
- feat (frontend/): Phase 2 Core Layout & Chat — เสร็จสมบูรณ์ ✅
  - Root layout: collapsible sidebar + navbar + main content area
  - ChatWindow: scrollable message area, empty state with Thai helpful text
  - MessageBubble: react-markdown + remark-gfm, agent badges/icons
  - InputArea: auto-resize textarea, Enter to send, streaming indicator
  - Full SSE streaming wired: send message → stream → render → finalize
  - Status bar: processing (pulse dot), done (green), error (red)
  - npm run build + npm run lint ผ่านทั้งหมด (exit code 0)

## [v0.32.1] — 31 มีนาคม 2569 · feat
- feat (frontend/): Phase 1 Setup & Foundation — เสร็จสมบูรณ์ ✅
  - Next.js 16 + TypeScript + Tailwind CSS v4 + ESLint
  - Dark theme: slate/zinc/blue palette + agent colors
  - Inter + JetBrains Mono fonts
  - lib/api.ts (242 lines) — typed API client สำหรับ 16+ Flask endpoints
  - lib/utils.ts (119 lines) — helpers: cn, formatBytes, fileIcon, agentLabel, sanitizeHtml
  - hooks/useSSE.ts (237 lines) — SSE streaming hook พร้อม event parsing
  - npm run build + npm run lint ผ่านทั้งหมด (exit code 0)

## [v0.32.0] — 31 มีนาคม 2569 · feat (planned)
- feat (frontend): วางแผน migrate จาก index.html (3,224 lines) → Next.js App Router + TypeScript + Tailwind
- docs (plans/nextjs_migration.md): สร้างแผน 4 Phase พร้อม Definition of Done ทุก Phase
  - Phase 1: Setup & Foundation — สร้าง frontend/, config Tailwind, สร้าง useSSE hook, API client
  - Phase 2: Core Layout & Chat — Sidebar, ChatWindow, MessageBubble, InputArea, wire SSE streaming
  - Phase 3: Advanced Features — PreviewPanel, WorkspaceModal, FormatModal, ConfirmBar, session management
  - Phase 4: Polish & Testing — Keyboard shortcuts, error boundaries, docs update, backend tests
- docs (AGENTS.md): เพิ่ม Mandatory Workflow Rules 7 ข้อ (v0.31.1)
- fix (index.html): block `data:` URIs ใน `_sanitizeHtml` (v0.31.1)
- fix (index.html): เปลี่ยน error messages จาก `innerHTML` → `textContent` (v0.31.1)
- fix (db.py): ลบ dead function `_handle_corrupt_db()` (v0.31.1)

## [v0.31.1] — 31 มีนาคม 2569 · docs/fix
- docs (AGENTS.md): เพิ่ม Mandatory Workflow Rules 7 ข้อ — ห้ามแตะ .env, ถามให้ชัดก่อนทำ, วางแผนก่อนแก้, ทำตามแผน, อัปเดต docs ทุกครั้ง, commit ทุกอย่าง, สรุปให้ user เข้าใจง่าย
- fix (index.html): block `data:` URIs in `_sanitizeHtml` — ป้องกัน XSS ผ่าน data: URI payload
- fix (index.html): เปลี่ยน error messages จาก `innerHTML` เป็น `textContent` — ป้องกัน HTML injection ใน error display
- fix (db.py): ลบ dead function `_handle_corrupt_db()` ที่ไม่มี caller

## [v0.31.0] — 31 มีนาคม 2569 · fix/docs
- fix (app.py): UTF-8 safe byte truncation สำหรับ `pending_doc` — ป้องกัน multi-byte character ถูกตัดกลางตัวอักษร
- fix (app.py): เพิ่ม `try/finally` ใน SSE generator — เรียก `db.fail_job()` เมื่อ client disconnect ป้องกัน zombie jobs
- fix (app.py): PM subtask failure cleanup — ลบ temp files ที่สร้างไว้เมื่อ subtask ล้มเหลว + yield error event
- fix (app.py): `handle_pm_save` yield error event เมื่อ skip unsafe/missing temp path แทนที่จะเงียบ
- fix (app.py): เพิ่ม `_truncate_at_word()` — ตัด conversation history ที่ word boundary แทน hard cut กลางคำ
- fix (app.py): เพิ่ม 6 workspace/file management routes — `GET/POST /api/workspace`, `GET /api/files`, `GET /api/files/stream`, `GET /api/workspaces`, `POST /api/workspace/new`
- fix (app.py): wire `get_session_workspace(session_id)` ใน `chat()` route — per-session workspace isolation
- fix (app.py): `api_set_workspace` ใช้ `set_session_workspace()` เมื่อมี session_id — ป้องกัน global workspace race condition
- fix (app.py): `handle_save` guard `local_agent_mode` — reject write operations เมื่อ Local Agent Mode เปิดอยู่
- fix (app.py): ป้องกัน double `db.fail_job()` — เพิ่ม `_job_failed` flag ใน generator finally block
- fix (app.py): CORS origins configurable ผ่าน env var `CORS_ORIGINS` แทน hardcoded localhost
- fix (app.py): ลบ duplicate `import logging`
- fix (core/shared.py): เพิ่ม per-session workspace state (`_session_workspaces` dict + lock) + `get_session_workspace()` / `set_session_workspace()`
- fix (core/shared.py): Lazy-initialized OpenAI client — `get_client()` สร้าง client ครั้งแรกเมื่อเรียก + validate API key
- fix (core/utils.py): `web_search` `max_results` cap เปลี่ยนจาก 10 → 5 ให้ตรงกับ tool definition
- fix (db.py): เพิ่ม `_db_write_lock` (threading.Lock) ครอบทุก write operation — ป้องกัน SQLite concurrent write corruption
- fix (db.py): ลบ duplicated `create_job` dead code (lines 139-151)
- fix (converter.py): PDF input size limit 100K chars — ป้องกัน worker crash จาก input ขนาดใหญ่
- fix (converter.py): Wrap PDF runtime errors ใน `try/except Exception` — catch weasyprint runtime failure
- fix (converter.py): `_strip_inline` ใช้ iterative loop แทน single-pass regex — รองรับ nested markdown
- fix (mcp_server.py): เพิ่ม `UnicodeDecodeError` handler ใน `fs_read_file` — ป้องกัน crash จาก binary file
- fix (agents/base_agent.py): ย้าย tool authorization check ก่อน `messages.append()` — ป้องกัน conversation history pollution
- fix (local_agent.py): เพิ่ม file read size limit 80K chars ใน `fs_read_file`
- fix (local_agent.py): เพิ่ม `UnicodeDecodeError` handler ใน `fs_read_file`
- fix (local_agent.py): `_ALLOWED_ORIGINS` เปลี่ยนเป็น function `_get_allowed_origins()` — อ่าน env var ทุกครั้งแทน import-time
- fix (index.html): เพิ่ม `_sanitizeHtml()` ใน `loadSession()` — ป้องกัน XSS จาก session history
- fix (index.html): bump version tag เป็น v0.31.0
- fix (requirements.txt): เพิ่ม minimum version pins ทุก package (flask>=3.0, openai>=1.30, ฯลฯ)
- docs: สร้าง Level 1 Standard documentation suite 7 ไฟล์ — README, ARCHITECTURE, BACKEND_MANUAL, FRONTEND_MANUAL, USER_GUIDE, CHANGELOG, EXECUTION_SUMMARY
- docs: ขยาย AGENTS.md จาก 26 → 170 lines — เพิ่ม build/test commands, code style, architecture patterns, security guidelines

---

## [v0.30.4] — 31 มีนาคม 2569 · ux
- ux (index.html): ย้าย typing indicator (•••) ออกจาก chat bubble — ซ่อน `.typing-indicator` ด้วย `display: none !important`
- ux (index.html): status bar เหนือ input เปลี่ยน pulsing dot เป็น CSS spinner (`status-spin` animation) เพื่อแสดงสถานะกำลังประมวลผลได้ชัดเจนขึ้น

---

## [v0.30.3] — 31 มีนาคม 2569 · fix
- fix (app.py): PDF serve เพิ่ม `conditional=True, max_age=60` — browser cache ETag/304 ทำให้เปิดครั้งที่ 2 ทันที
- fix (index.html): PDF panel ว่างเปล่าระหว่างโหลด — เพิ่ม loading spinner พร้อม PDF icon ก่อน iframe พร้อม
- fix (gunicorn.conf.py): อัปเดต comment ให้ตรงกับความจริง (gevent workers ไม่ block SSE)

---

## [v0.30.2] — 31 มีนาคม 2569 · feat/fix
- feat (app.py): เพิ่ม `GET /api/serve/<filename>` — serve raw file จาก workspace ใช้สำหรับ PDF/image inline preview
- fix (index.html): PDF preview แสดงข้อความ garbled จาก pdfplumber — เปลี่ยนเป็นใช้ browser PDF viewer ผ่าน `<iframe src="/api/serve/file.pdf">` แทน
- fix (index.html): ซ่อน tabs แสดงผล/ข้อความ สำหรับ PDF เช่นเดียวกับ docx/xlsx

---

## [v0.30.1] — 31 มีนาคม 2569 · fix
- fix (app.py): เขียนทับไฟล์ .docx ด้วย plain text — `handle_save` ตอนนี้ detect extension ของ `overwrite_filename` และ re-convert ด้วย converter ให้ถูก format
- fix (mcp_server.py): preview แสดง "Package not found" — เพิ่ม fallback อ่าน plain text เมื่อ python-docx parse ไม่ได้ (รองรับไฟล์ที่ถูก corrupt หรือ format ไม่ถูกต้อง)

---

## [v0.30.0] — 31 มีนาคม 2569 · feat
- feat (db.py): เพิ่ม `get_sessions()` + `get_session_jobs()` — query sessions grouped by session_id พร้อม first message, last agent, job count
- feat (app.py): เพิ่ม `GET /api/sessions` และ `GET /api/sessions/<session_id>` endpoints
- feat (index.html): Session list ใน sidebar — แสดงประวัติ sessions พร้อม colored dot ตาม agent, วันที่, จำนวนงาน
- feat (index.html): ปุ่ม "+ Session ใหม่" — เริ่ม session ใหม่ พร้อมล้าง chat และ conversation history
- feat (index.html): คลิก session เดิม → โหลดประวัติบทสนทนา, restore conversation context, ต่อบทสนทนาได้ทันที
- feat (index.html): Session list refresh อัตโนมัติหลังทุก response และตอน page load

---

## [v0.29.4] — 31 มีนาคม 2569 · fix
- fix (index.html): input footer ไม่เลื่อนเมื่อ preview เปิด — เพิ่ม `body.preview-open .input-footer { right: 420px }`
- fix (index.html): navbar content เลื่อนมากลางจอ — ลบ `right: 420px` ออกจาก navbar (navbar z-index 50 อยู่เหนือ panel อยู่แล้ว)
- fix (index.html): tab แสดงผล/ข้อความ ซ้อนทับกัน — ซ่อน tab สำหรับไฟล์ที่ไม่ใช่ .md (docx/xlsx/pdf/txt ใช้ raw text เท่านั้น)

---

## [v0.29.3] — 31 มีนาคม 2569 · fix
- fix (index.html): preview panel ทับ navbar — เลื่อน panel ลงมาที่ `top: 60px` + `height: calc(100vh - 60px)` ให้อยู่ใต้ navbar พอดี
- fix (index.html): navbar ทับพื้นที่ panel — เพิ่ม `body.preview-open .navbar { right: 420px }` ให้ navbar หดออกจากพื้นที่ panel

---

## [v0.29.2] — 31 มีนาคม 2569 · fix
- fix (index.html): ปุ่มปิด preview panel ถูก squeeze หายไป — restructure header เป็น 2 rows: row1 = icon+ชื่อไฟล์+ปุ่ม ✕, row2 = tabs+copy เพื่อรับประกันว่าปุ่มปิดแสดงผลเสมอ

---

## [v0.29.1] — 31 มีนาคม 2569 · fix
- fix (index.html): preview panel กระพริบทุก ms — เกิดจาก `renderFileList` เรียก `openPreview` ทุกครั้งที่ file SSE heartbeat มา แก้โดยเปลี่ยนเป็น `_silentRefreshPreview` ที่ trigger เฉพาะเมื่อ file size เปลี่ยน
- fix (app.py): `/api/preview` return `size` เพิ่มเพื่อให้ frontend track การเปลี่ยนแปลงได้แม่นยำ

---

## [v0.29.0] — 31 มีนาคม 2569 · feat
- feat (index.html): เพิ่ม File Preview Panel — คลิกไฟล์ใน sidebar เปิด panel ด้านขวา แสดง markdown rendered + raw text, copy ได้, ปิดด้วย Esc หรือ ✕
- feat (index.html): file item ใน sidebar มี icon ตาม extension + active highlight เมื่อเปิด preview
- feat (index.html): preview panel auto-refresh เมื่อไฟล์ถูก update, auto-close เมื่อถูกลบ
- feat (app.py): เพิ่ม `GET /api/preview?file=` endpoint — อ่านเนื้อหาไฟล์ใน workspace รองรับ .docx/.xlsx/.pdf เช่นเดียวกับ fs_read_file

---

## [v0.28.4] — 31 มีนาคม 2569 · fix
- fix (agents/base_agent.py): เพิ่ม retry 1 ครั้งเมื่อ model return empty response หลัง tool call — แก้ปัญหา Qwen3 thinking-mode, free-tier rate limit glitch และ transient API error ทำให้แสดง "ขออภัย ระบบไม่ได้รับคำตอบ" แม้ agent อ่านไฟล์สำเร็จแล้ว

---

## [v0.28.3] — 31 มีนาคม 2569 · feat
- feat (core/shared.py): เพิ่ม `AGENT_MAX_TOKENS`, `CHAT_MAX_TOKENS`, `ORCHESTRATOR_MAX_TOKENS` — configure ผ่าน `.env` แทน hardcode
- feat (app.py): wire token limits per agent type — document agents ใช้ `AGENT_MAX_TOKENS`, chat ใช้ `CHAT_MAX_TOKENS`
- feat (core/orchestrator.py): wire `ORCHESTRATOR_MAX_TOKENS`
- docs (.env.example): เพิ่ม output token limit section พร้อม guide ต่อ model

---

## [v0.28.2] — 31 มีนาคม 2569 · fix
- fix (mcp_server.py): จำกัด plain-text read ที่ 80,000 ตัวอักษร (~20K tokens) + แสดงคำเตือนเมื่อไฟล์ถูกตัด — ป้องกัน context window overflow
- fix (agents/base_agent.py): เพิ่ม tool_result display จาก 200 → 500 ตัวอักษร + แสดง `…` เมื่อ preview ถูกตัด — แก้ปัญหา user เข้าใจผิดว่า agent ได้รับเนื้อหาไม่ครบ
- note: `.docx` UnicodeDecodeError แก้แล้วใน v0.28.1 แต่ต้อง restart server เพื่อให้ Python module โหลดใหม่

---

## [v0.28.1] — 31 มีนาคม 2569 · fix
- fix (mcp_server.py): `fs_read_file` ไม่สามารถอ่านไฟล์ binary ได้ — เพิ่ม text extraction สำหรับ `.docx` (python-docx), `.xlsx` (openpyxl), `.pdf` (pdfplumber) แทนการเปิดเป็น UTF-8 ตรงๆ ซึ่งทำให้ได้รับ `UnicodeDecodeError`

---

## [v0.28.0] — 31 มีนาคม 2569 · feat
- feat: Delete with HITL — agent เรียก `request_delete` → frontend แสดง confirm modal → user ยืนยัน → POST `/api/delete` → ไฟล์ถูกลบ + sidebar refresh
- feat: Overwrite existing file — agent อ่านไฟล์เดิม (`read_file`) → สร้างเนื้อหาใหม่ → confirm bar แสดงปุ่ม [💾 สร้างไฟล์ใหม่] [🔄 เขียนทับ filename] [✕ ไม่ต้องการ]
- feat (app.py): เพิ่ม `request_delete` ใน MCP_TOOLS + READ_ONLY_TOOLS; intercept `__DELETE_REQUEST__:` marker → SSE `delete_request` event; `handle_save` รับ `overwrite_filename` param → ใช้ `update_file` แทน `create_file`; เพิ่ม `POST /api/delete` endpoint
- feat (agents/base_agent.py): `read_file` tool_result event ส่ง `filename` field เพิ่มให้ frontend track `lastReadFile`
- feat (core/utils.py): `request_delete` tool handler → คืน `__DELETE_REQUEST__:filename` marker
- feat (index.html): state `lastReadFile`/`pendingOverwriteFile`; delete confirm modal; overwrite button ใน save confirm bar; `_showDeleteConfirmModal()`; `confirmOverwrite()`

---

## [v0.27.1] — 31 มีนาคม 2569 · fix
- fix (agents/base_agent.py): ลบ `if text_streamed: return` ออก — แก้ปัญหา agent ค้นเว็บแล้วไม่สร้างเอกสาร เพราะ early return ตัดการทำงาน iteration ถัดไปที่จะ generate เอกสารจริง

---

## [v0.27.0] — 31 มีนาคม 2569 · feat
- feat: เพิ่ม Document Agent — รองรับเอกสารทั่วไปที่ไม่ใช่งาน HR/บัญชี/manager advisory
  - ครอบคลุม: รายงานการประชุม, คู่มือ/SOP, แผนธุรกิจ, ใบเสนอราคา, รายงานโครงการ, Executive Summary ฯลฯ
- feat (prompts/orchestrator.md): เพิ่ม document routing + แก้ manager ให้เป็น advisory เท่านั้น
- feat (agents/document_agent.py): สร้างใหม่
- feat (prompts/document_agent.md): สร้างใหม่
- feat (core/agent_factory.py): register DocumentAgent
- feat (index.html): เพิ่ม agentMap entry + CSS color (amber/gold) สำหรับ Document Agent

---

## [v0.26.0] — 31 มีนาคม 2569 · fix
- fix (index.html): หลัง save สำเร็จ force-poll `/api/files` เพื่อ refresh sidebar — ป้องกัน "false save" จาก SSE workspace desync
- fix (core/shared.py): persist workspace path ไปยัง `data/.workspace_state` — หลัง server restart workspace จะ restore กลับ path เดิมแทนที่จะ reset เป็น default

---

## [v0.25.9] — 31 มีนาคม 2569 · fix
- fix (agents/base_agent.py): เพิ่ม fallback text เมื่อ model return empty response (ไม่มี text และไม่มี tool_calls) — แทนที่จะ silent return ที่ทำให้หน้าจอว่างเปล่า
- fix (index.html): `done` handler แสดง inline error เมื่อ agent ตอบ 0 ตัวอักษร แทนที่จะแสดง status "0 ตัวอักษร" โดยไม่มีอะไรในกล่องคำตอบ
- fix (prompts/orchestrator.md): เพิ่ม routing rule — คำขอ "สร้างเอกสาร/ไฟล์" ที่ไม่ระบุ domain → ส่งไป manager ไม่ใช่ chat

---

## [v0.25.8] — 30 มีนาคม 2569 · fix
- fix (index.html): `_looksLikeDraft()` เพิ่ม 2 เงื่อนไขเพิ่มเติม — detect `**bold heading**` บนบรรทัดเดียว และ 20+ บรรทัด — แก้ปัญหา confirm bar ไม่โผล่เมื่อเอกสาร Thai ใช้ bold แทน `#` heading

---

## [v0.25.7] — 30 มีนาคม 2569 · fix
- fix (index.html): confirm bar แสดงเฉพาะเมื่อ response เป็น draft จริงๆ — ต้องมี markdown heading (`# ...`) และยาวกว่า 300 ตัวอักษร — ป้องกันไม่ให้โผล่ตอน agent ถามคำถามกลับ

---

## [v0.25.6] — 30 มีนาคม 2569 · fix
- fix (index.html): status pill ✅ เสร็จสิ้น ค้างอยู่จนกว่าจะมี task ใหม่ แทนที่จะ fade หายใน 4 วินาที

---

## [v0.25.5] — 30 มีนาคม 2569 · feat
- feat (index.html): status bar เปลี่ยนเป็น pill ที่มองเห็นได้ชัด — 3 states: processing (purple pulsing dot), done (green, fade หลัง 4s), error (red)
- feat (index.html): `_setStatus()` helper จัดการ class อัตโนมัติจากข้อความ — ไม่ต้องแก้ backend

---

## [v0.25.4] — 30 มีนาคม 2569 · perf
- perf (app.py): Orchestrator รับ history แค่ 3 messages ล่าสุด (ลดจาก 20) — ลด token ที่ส่งไป routing LLM call ให้ได้ first token เร็วขึ้น, agent ยังรับ history เต็ม 20 เหมือนเดิม

---

## [v0.25.3] — 30 มีนาคม 2569 · fix
- fix (index.html): ลบ popup ทั้งหมด (single-agent + PM multi-file) — ถ้าพิมพ์ข้อความใหม่ขณะมี draft/pending ค้างอยู่ ระบบ discard เงียบๆ แล้วดำเนินการต่อเลย
- feat (setup.sh): เพิ่ม cron job ลบไฟล์ใน `temp/` ที่เก่ากว่า 60 นาที ทุก 30 นาที — ทำงานอัตโนมัติบน server แทน popup

---

## [v0.25.2] — 30 มีนาคม 2569 · fix
- fix (index.html): ลบ popup "มีเอกสารที่ยังไม่ได้บันทึก" สำหรับ single-agent draft — ถ้าพิมพ์ข้อความใหม่ขณะที่มี draft ค้างอยู่ ระบบจะ discard draft เงียบๆ แล้วดำเนินการต่อเลย ไม่ขัดจังหวะ
- fix (index.html): popup ยังคงทำงานสำหรับ PM multi-file pending เท่านั้น (มีไฟล์จริงบน disk ที่ต้องจัดการ)

---

## [v0.25.1] — 30 มีนาคม 2569 · fix
- fix (index.html): confirm bar ย้ายไปแสดงใน `aiBody` แทน outer container — ปรากฏถูกต้องที่ด้านล่างเนื้อหา ไม่ลอยที่มุมบน
- fix (index.html): เพิ่ม edit hint "✏️ หรือพิมพ์ข้อความด้านล่างเพื่อแก้ไขเอกสาร" ใน confirm bar
- fix (index.html): `modalSkipBtn` เรียก `cancelPending()` ก่อน `sendMessage` — ลบ confirm bar เก่าออกเมื่อ skip ไปทำงานใหม่
- fix (index.html): `_appendSaveConfirmBar` ลบ confirm bar เก่าทั่วทั้งหน้าก่อนสร้างใหม่ (querySelectorAll แทน querySelector)

---

## [v0.25.0] — 30 มีนาคม 2569 · feat
- feat (index.html): หลัง AI สร้างเอกสาร Draft เสร็จ จะแสดง confirm bar "ต้องการสร้างไฟล์นี้ไหม?" พร้อมปุ่ม สร้างไฟล์ / ไม่ต้องการ ในตัว message แทนที่จะรอให้พิมพ์ "บันทึก"
- feat (index.html): กดปุ่ม "สร้างไฟล์" → เปิด format popup เลือก .md / .txt / .docx / .xlsx / .pdf ก่อนบันทึก
- feat (app.py): `_suggest_filename` ใช้ last 5 conversation history เป็น fallback ถ้าเอกสารไม่มี heading — ชื่อไฟล์สะท้อน context การสนทนา
- feat (app.py): `handle_save` รับ `history` param และส่งต่อไปยัง `_suggest_filename`

---

## [v0.24.3] — 30 มีนาคม 2569 · fix
- fix (core/utils.py): `inject_date` เพิ่มปี ค.ศ. และ "Today is March 30, 2026" เป็นภาษาอังกฤษ — แก้ปัญหา AI ค้นหาข่าวปีเก่า เพราะ AI ไม่รู้ว่า พ.ศ. 2569 = ค.ศ. 2026

---

## [v0.24.2] — 30 มีนาคม 2569 · fix
- fix (core/utils.py): รวม `inject_date()` เป็นฟังก์ชันกลางที่เดียว — ย้ายออกจาก `base_agent.py` และ `orchestrator.py` (DRY) — ใช้ `ZoneInfo("Asia/Bangkok")` สำหรับ timezone ที่ถูกต้อง พร้อม fallback และ warning log
- fix (core/utils.py): `_BANGKOK_TZ` คำนวณครั้งเดียวตอน module load แทนการ import ทุก call — ป้องกัน `ZoneInfoNotFoundError` แบบ silent
- fix (agents/base_agent.py, core/orchestrator.py): ลบ `_inject_date` ที่ซ้ำซ้อน — import `inject_date` จาก `core.utils` แทน
- fix (prompts/chat_agent.md): แก้การอ้างอิงวันที่ที่คลุมเครือ — ลบ "บรรทัดแรก" placeholder, ใช้ภาษาธรรมชาติที่ AI ตีความถูกต้อง
- fix (requirements.txt): เพิ่ม `tzdata` เพื่อให้ `ZoneInfo("Asia/Bangkok")` ทำงานได้บน Alpine/minimal Linux

---

## [v0.24.1] — 30 มีนาคม 2569 · fix
- fix (local_agent.py): แทนที่ CORS wildcard `*` ด้วย origin allowlist — รับเฉพาะ `localhost:5000` และ `127.0.0.1:5000` (กำหนดค่าได้ผ่าน `LOCAL_AGENT_ALLOWED_ORIGINS`) — `OPTIONS` และ `POST /files` ส่ง 403 หาก Origin ไม่อยู่ใน allowlist
- fix (app.py): `/api/workspace/new` ตรวจสอบ `root` ว่าอยู่ใน `_ALLOWED_ROOTS` ก่อนสร้าง folder (สองชั้น: root allowlist + `_is_allowed_workspace_path`) — ป้องกัน path traversal จาก client
- fix (app.py): `handle_save` และ `handle_pm_save` yield raw dicts แทน pre-formatted SSE — caller ตรวจ `event['type']` แล้วค่อย `format_sse()` — `db.complete_job()` เรียกเฉพาะตอน save สำเร็จ, `db.fail_job()` เรียกตอนล้มเหลว
- fix (index.html): bump version tag เป็น v0.24.1

---

## [v0.24.0] — 30 มีนาคม 2569 · feat
- feat (index.html): Collapsible sidebar — ปุ่ม `☰` ที่ navbar-left พับ/ขยาย sidebar ด้วย animation 0.25s ease
- feat (index.html): Sidebar, main content, navbar, และ input footer เคลื่อนที่พร้อมกันเมื่อพับ
- feat (index.html): จำสถานะ sidebar ไว้ใน `localStorage` key `sidebarCollapsed` — reload แล้วยังคงสถานะเดิม
- fix (index.html): แก้ `navbar-left align-items: baseline` → `center` ให้ปุ่ม toggle ตรงกลางแนวตั้ง
- fix (index.html): เพิ่ม `aria-label` บนปุ่ม toggle สำหรับ accessibility

---

## [v0.23.0] — 27 มีนาคม 2569 · feat
- feat: **Local Agent Mode** — เมื่อ `local_agent_mode: true` ถูกส่งจาก browser, server จะใช้ `LOCAL_AGENT_TOOLS` (web_search + local_delete เท่านั้น) แทน `READ_ONLY_TOOLS` — ตัด `list_files`/`read_file`/`create_file`/`update_file` ออกทั้งหมด เพราะถูกแทนที่ด้วย browser context injection + save intercept
- feat: `local_delete` tool ใหม่ใน `app.py` + `core/utils.py` — เมื่อ AI เรียก tool นี้ server คืน marker `__LOCAL_DELETE__:{filename}` แทนการลบจาก WSL; `app.py` แปลง marker เป็น SSE event `type: local_delete`
- feat (index.html): ส่ง `local_agent_mode: true` ใน reqBody เมื่อ `localAgentActive`
- feat (index.html): `_localDelete(filename)` — POST ไปยัง `localhost:7000` action:delete แล้ว refresh sidebar
- feat (index.html): handle SSE event `type: local_delete` ใน stream loop — browser ลบไฟล์จริงบน Windows แทน server

---

## [v0.22.4] — 27 มีนาคม 2569 · feat
- feat (index.html): inject เนื้อหาไฟล์จริง (text files ≤50KB) เข้า AI context พร้อมกับ file list — AI อ่านเนื้อหาไฟล์ได้โดยไม่ต้องเรียก `read_file` tool (ซึ่งอ่านจาก WSL ผิด workspace)
- รองรับนามสกุล: md, txt, py, js, ts, json, csv, html, xml, yaml, yml, ini, cfg, log, sh, bat, sql
- ไฟล์ binary หรือใหญ่เกิน 50KB แนบแค่ metadata

---

## [v0.22.3] — 27 มีนาคม 2569 · feat
- feat (index.html): inject local workspace file list เป็น context ให้ AI ทุกครั้งที่ส่ง message เมื่อ `localAgentActive` — AI รู้ว่ามีไฟล์อะไรบน Windows โดยไม่ต้องเรียก `list_files` tool

---

## [v0.22.2] — 27 มีนาคม 2569 · feat
- feat (index.html): sidebar แสดงไฟล์จาก local agent (poll `localhost:7000` ทุก 3 วินาที) แทน SSE จาก server เมื่อ `localAgentActive` — ผู้ใช้เห็นไฟล์ Windows workspace จริงๆ ใน sidebar

---

## [v0.22.1] — 27 มีนาคม 2569 · fix
- fix (index.html): แสดง local agent workspace path ใน header path text เมื่อ detect agent สำเร็จ — แทนที่ server workspace path ด้วย Windows workspace path

---

## [v0.22.0] — 27 มีนาคม 2569 · feat
- feat: `local_agent.py` — HTTP server (localhost:7000) สำหรับจัดการไฟล์บนเครื่อง user โดยตรง, sandbox ด้วย `_validate_path()`, stdlib เท่านั้น (ไม่ต้อง pip install เพิ่ม), รองรับ 5 actions: list/create/read/update/delete, CORS headers ครบ
- feat (index.html): detect local agent ตอนโหลดหน้า (`_checkLocalAgent`), badge `💻 Local` ที่ header เมื่อ agent รัน, intercept save → บันทึกลงเครื่อง user แทน server เมื่อ `localAgentActive=true`, fallback server-side เมื่อ agent ไม่รัน
- docs: เพิ่ม `plans/local_agent_plan.md` — แผน 4 Phase (v0.22–v0.25)

---

## [v0.21.0] — 27 มีนาคม 2569 · test
- test (D2): รัน concurrency test `test_concurrency_pm.py` ครบทั้ง 4 TC บน gunicorn+gevent — **ผ่านทุก TC**
  - TC-1 (2 PM พร้อมกัน): ✅ PASS (17.5s / 74.0s)
  - TC-2 (PM + workspace switch กลางคัน): ✅ PASS — snapshot isolation ทำงานถูกต้อง
  - TC-3 (3 PM พร้อมกัน): ✅ PASS (39.9s / 72.1s / 48.7s)
  - TC-4 (memory leak baseline): ✅ PASS — memory growth +1MB จาก 10 sequential requests (เกณฑ์ <50MB)
- docs: อัปเดต `plans/deployment_prep_plan.md` — D2 marked ✅ DONE, บันทึก test results ครบถ้วน

---

## [v0.20.1] — 27 มีนาคม 2569 · fix
- fix: `crypto.randomUUID is not a function` เมื่อเข้าผ่าน HTTP — เพิ่ม fallback UUID generator สำหรับ non-secure context (HTTP)

---

## [v0.20.0] — 27 มีนาคม 2569 · deploy
- deploy (D3): audit workspace global state risk — ผล: PM loop ปลอดภัยแล้ว เพราะ `workspace` ถูก capture ครั้งเดียวที่ต้น request (line 381) และส่งผ่าน parameter ตลอด ไม่มี agent ใดเรียก `get_workspace()` เอง — เพิ่ม guard comment ใน `core/shared.py` และ `app.py` ป้องกัน regression ในอนาคต
- deploy (Nginx): สร้าง `nginx.conf` — reverse proxy หน้า gunicorn, แยก location สำหรับ SSE (`/api/chat`, `/api/files/stream`) ด้วย `proxy_buffering off` + `proxy_read_timeout 130s`, security headers, `client_max_body_size 1m`

---

## [v0.19.0] — 27 มีนาคม 2569 · deploy
- deploy (D4): rate limiting บน `/api/chat` — เพิ่ม `flask-limiter`, init `Limiter` ด้วย `get_remote_address`, apply `@limiter.limit("10 per minute")` บน `/api/chat`, เพิ่ม Thai error handler 429, configurable ด้วย `CHAT_RATE_LIMIT` env var

---

## [v0.18.0] — 27 มีนาคม 2569 · deploy
- deploy (D1): switch Flask dev server → gunicorn + gevent — เพิ่ม `gunicorn` + `gevent` ใน `requirements.txt`, สร้าง `gunicorn.conf.py` (2 workers, gevent, timeout 120s), อัปเดต `start.sh` ให้รัน `gunicorn --config gunicorn.conf.py "app:app"` แทน `python app.py`
- deploy (D5): แก้ `.env.example` — แยก `OPENROUTER_TIMEOUT` และ `ALLOWED_WORKSPACE_ROOTS` ที่ถูก merge เป็นบรรทัดเดียวออกจากกัน, จัดกลุ่ม env vars ตาม section, เพิ่ม gunicorn vars (`GUNICORN_WORKERS`, `GUNICORN_CONNECTIONS`, `GUNICORN_TIMEOUT`, `GUNICORN_LOG_LEVEL`), เพิ่ม `MAX_PENDING_DOC_BYTES`, `WEB_SEARCH_TIMEOUT`, `FLASK_DEBUG`, `FLASK_HOST`, `FLASK_PORT`
- fix: `Orchestrator.route()` crash เมื่อ OpenRouter return `content=None` — เพิ่ม null check + `TypeError` ใน except, fallback เป็น chat agent แทน crash

---

## [v0.17.0] — 27 มีนาคม 2569 · fix
- fix (M1): N+1 queries ใน `db.get_history` — เปลี่ยนเป็น batch query ด้วย `IN (...)` clause รวบรวม files ทั้งหมดใน 1 query แล้ว group by job_id ใน Python
- fix (M2): `OPENROUTER_API_KEY` ไม่มี startup validation — เพิ่ม `logger.error` ตอน module load ถ้า key ไม่ถูก set
- fix (M3): `reader.cancel()` ขาดใน catch block — เพิ่ม `reader.cancel().catch(()=>{})` ใน `catch(err)` ป้องกัน dangling stream
- fix (M4): `handle_pm_save` ดึง agent type จากชื่อไฟล์ fragile — เพิ่ม `agent_types` parameter ส่งผ่าน frontend (`pendingFileAgents`) → reqBody → backend แทนการ split filename
- fix (M5): ไม่มี size limit บน `pending_doc` — เพิ่ม `_MAX_PENDING_DOC_BYTES` (200KB default, override ด้วย env) ตัด pending_doc ก่อน process
- fix (H6): `copyOutput()` copy แค่ subtask สุดท้าย — เปลี่ยนเป็น `lastContainer.querySelectorAll('.output-area')` รวม text ทุก subtask ด้วย `---` separator

---

## [v0.16.0] — 27 มีนาคม 2569 · fix
- fix (H2): `stream_response` ไม่มี exception handling — เพิ่ม `try/except` ครอบทั้ง API call + chunk loop; PM subtask loop ใน `app.py` เพิ่ม error recovery emit `error` + `subtask_done` แล้ว `continue` subtask ถัดไป
- fix (H3): Partial document เข้า `pendingDoc` เมื่อ stream error — เพิ่ม `hadError` flag; `done` handler guard `&& !hadError` ก่อน set pending state
- fix (H4): `global WORKSPACE_PATH` แก้ local binding ใน app.py เท่านั้น — เปลี่ยนมาใช้ `set_workspace()` / `get_workspace()` จาก `core.shared` ทำให้ทุก module เห็น workspace ที่อัปเดตแล้ว
- fix (H5): `GeneratorExit` ไม่ถูก handle — เพิ่ม `except GeneratorExit: raise` ป้องกัน stream cleanup ผิดพลาด
- fix (I1): `run_with_tools` silent exhaustion — เพิ่ม warning log + emit `status` แจ้ง user เมื่อ max_iterations หมด
- fix (I2): ไม่ check `finish_reason` — track per-chunk `finish_reason`; log + emit status เมื่อ `length`
- fix (I3): `content: None` — เปลี่ยนเป็น `content: ""` ป้องกัน provider ที่ไม่รับ null

---

## [v0.15.2] — 27 มีนาคม 2569 · fix
- fix (H1): `_web_search` ไม่มี timeout — เพิ่ม `DDGS(timeout=_WEB_SEARCH_TIMEOUT)` (default 15 วินาที, override ได้ด้วย env `WEB_SEARCH_TIMEOUT`) — ป้องกัน search request ค้างแบบ infinite ซึ่งบล็อก Flask worker thread

---

## [v0.15.1] — 27 มีนาคม 2569 · fix
- fix (C2): PM task output ไม่ถูก push เข้า `conversationHistory` — เพิ่ม `pmOutputAccumulator` รวบรวม output ของแต่ละ subtask ใน `subtask_done` handler แล้วใช้ accumulator แทน `outputText` เมื่อ `done` fired — PM context พร้อมสำหรับ turn ถัดไปแล้ว

---

## [v0.15.0-c1] — 26 มีนาคม 2569 · fix
- fix (C1): `_is_save_intent` false positive — แยก `'ok'` และ `'save'` ออกจาก substring set ใช้ `\b(?:ok|save)\b` regex แทน — ป้องกัน "stock", "look", "unsaved" ทริก save intent โดยไม่ตั้งใจ

---

## [v0.14.1] — 26 มีนาคม 2569 · fix
- fix: fake tool-call JSON (`{"request": "web_search", ...}`) แสดงเป็น plain text ระหว่าง live streaming — เพิ่ม real-time strip ใน `text` event handler (display-only; `outputText` ยังคง raw สำหรับ `text_replace`/`done`/`subtask_done` pipeline)

---

## [v0.14.0] — 26 มีนาคม 2569 · feat
- feat: PM Agent subtask cards — กรอบสีแยกชัดเจนสำหรับแต่ละ sub-agent ที่ถูกเรียกผ่าน PM (HR=เขียว, Accounting=ม่วง, Manager=ชมพู)
- feat: card header แสดง agent icon + ชื่อ + task description; card body คือ output ของ sub-agent
- feat: `web_search_sources` chips และ `tool_result` lines แทรกใน card แทน aiBody โดยตรง (`currentOutputEl.before()`)
- fix: ลบ `<hr>` separator ระหว่าง subtasks — ถูกแทนที่ด้วย card borders
- fix: `aiBody.insertBefore(x, currentOutputEl)` → `currentOutputEl.before(x)` ใน web_search_sources + tool_result — ทำงานถูกต้องแม้ currentOutputEl อยู่ใน nested card

---

## [v0.13.3] — 26 มีนาคม 2569 · feat
- feat: แสดงแหล่งที่มา web search เป็น pill chips ก่อนคำตอบ — SSE event `web_search_sources` ใหม่พร้อม query + domain pills ที่คลิกได้
- feat: `extract_web_sources()` ใน `core/utils.py` parse `ที่มา:` lines จาก search result
- feat: `base_agent.run_with_tools` emit `web_search_sources` แทน `tool_result` สำหรับ web_search — แสดง domain chips ด้วย Material Icon `travel_explore`

---

## [v0.13.2] — 26 มีนาคม 2569 · fix
- fix: เพิ่ม client-side regex strip ใน `done` และ `subtask_done` handlers — ลบ fake tool call JSON ออกจาก `outputText` ก่อน markdown render เสมอ (ป้องกัน JSON โชว์ใน bubble แม้ `text_replace` server event ไม่ถึง)
- fix: `pendingDoc` และ `conversationHistory` รับ clean text เพราะ `outputText` ถูก strip ก่อน `done` handler ตั้งค่า `pendingDoc`

---

## [v0.13.1] — 26 มีนาคม 2569 · fix
- fix: HR/Accounting/Manager agents ไม่แสดง `{"request": "web_search", ...}` JSON เป็น plain text ในกล่องแชทอีกต่อไป
- fix: เพิ่ม `_FAKE_TOOL_CALL_RE` regex filter ใน `base_agent.run_with_tools` — detect และ strip fake tool call JSON หลังจบ streaming loop; ส่ง `text_replace` SSE event เพื่อ overwrite bubble content
- fix: `index.html` handle `text_replace` SSE event — replace `outputText` และ re-render bubble ทันที
- fix: เพิ่ม "กฎการเรียกใช้ tools" ใน prompts ของ HR/Accounting/Manager — ห้ามเขียน JSON tool call เป็น plain text

---

## [v0.13.0] — 26 มีนาคม 2569 · fix
- fix (C1): AgentFactory.get_agent ใช้ threading.Lock + double-checked locking — ป้องกัน race condition ใน threaded Flask
- fix (C2): ลบ dead function `stream_agent` ออกจาก app.py — refactor `handle_revise` ให้ใช้ `agent_instance.stream_response()` แทน; caller ใน `generate()` ใช้ dict แทน pre-formatted SSE strings
- fix (C3): เพิ่ม `timeout=60.0` ใน OpenAI client (configurable ผ่าน `OPENROUTER_TIMEOUT` env var) — ป้องกัน request ค้างไม่จบ
- fix (bonus): `handle_revise` forward `conversation_history` ไปยัง `stream_response` — agent มี session context ระหว่างแก้ไขเอกสาร
- fix (bonus): `handle_revise` มี exception handler แยก — API error ระหว่าง revision แสดง Thai error message แทนการ propagate ไป outer handler
- fix (bonus): แก้ bare `except:` ใน `_is_safe_temp_path` → `except (ValueError, TypeError):`
- fix (bonus): แก้ bare `except:` ใน `files_stream` watchdog handler → `except queue.Full:`
- fix (bonus): AgentFactory fallback ไปยัง ChatAgent ใส่ `logger.warning` แล้ว — visible ใน production logs
- fix (bonus): safe parse `OPENROUTER_TIMEOUT` env var ด้วย try/except — ไม่ crash ถ้า value ไม่ใช่ตัวเลข
- fix (bonus): แก้ bare `except:` ใน `base_agent.py` JSON parse → `except (json.JSONDecodeError, ValueError):`

---

## [v0.12.2] — 26 มีนาคม 2569 · fix
- fix (B1): wrap both SSE Response generators with `stream_with_context` — prevents silent crash under Gunicorn/production WSGI
- fix (B2): replace all `str(e)` in SSE error events with user-friendly Thai messages; log full traceback server-side with `exc_info=True`
- fix (B3): replace `except: pass` in `_cleanup_old_temp` with `except OSError as e: logger.warning(...)` — stops swallowing shutdown signals
- fix (bonus): fix `except: pass` in `list_workspaces()` → `except OSError`; fix `str(e)` leaks in `core/utils.py` (_web_search, execute_tool)

---
## [v0.12.1] — 26 มีนาคม 2569 · fix
- fix (A1): PM Agent ไม่สั่งให้ sub-agents บันทึกไฟล์แล้ว — แก้ `prompts/pm_agent.md` กฎข้อ 3 ป้องกัน sub-agents hallucinate write_file tool call
- fix (A2): HR/Accounting/Manager agents ไม่แสดง footer "พิมพ์ บันทึก" เมื่อรันเป็น PM subtask — ใช้ `[PM_SUBTASK]` marker ใน task description และ conditional footer ใน prompts

---
## [v0.12.0] — 26 มีนาคม 2569 · refactor
- **Major Refactoring**: แยกโครงสร้างโปรเจกต์เป็น Modular Architecture
- **Prompt Separation**: ย้าย System Prompts ทั้งหมดจาก `app.py` ไปเป็นไฟล์ `.md` ในโฟลเดอร์ `prompts/`
- **Agent Modularization**: แยก Logic ของแต่ละ Agent (HR, Accounting, Manager, PM, Chat) ออกเป็นโมดูลอิสระในโฟลเดอร์ `agents/`
- **Core Logic Extraction**: ย้ายฟังก์ชันส่วนกลาง, การจัดการ Workspace และ Shared Resources ไปยังโฟลเดอร์ `core/`
- **Robustness**: แก้ไขปัญหา SyntaxError ของ f-string ใน Python 3.10 โดยการเพิ่ม `format_sse` helper
- **Reliability**: ปรับปรุงระบบตรวจสอบความปลอดภัยของ Workspace Path ให้เข้มงวดและถูกต้องตามหลัก Path Traversal Protection

## [v0.11.1] — 26 มีนาคม 2569 · fix
- fix: chat agent responses no longer trigger save-to-file confirmation flow — skip pendingDoc when lastAgent === 'chat'
- fix: max_tokens ทุก agent (HR/Accounting/Manager/Chat) เพิ่มเป็น 10,000 — ป้องกัน context truncation สำหรับเอกสารยาว

---
## [v0.11.0] — 26 มีนาคม 2569 · feat
- feat: Chat Agent ใหม่ — Orchestrator route "chat" สำหรับการทักทายและสนทนาทั่วไป
- feat: CHAT_PROMPT — ตอบอย่างเป็นธรรมชาติ แนะนำระบบ ไม่สร้างเอกสาร
- feat: HR/Accounting/Manager agents acknowledge งานก่อน output เอกสาร
- feat: soften tone ใน HR/Accounting/Manager prompts — เปลี่ยนจาก directive เป็น collaborative
- feat: badge "💬 Assistant" สำหรับ chat route

---
## [v0.10.1] — 26 มีนาคม 2569 · fix
- fix: web_search infinite loop — เพิ่ม MAX_WEB_SEARCH_CALLS=3 guard ป้องกัน agent ค้นหาซ้ำไม่สิ้นสุด
- fix: detect model ที่ไม่รองรับ structured tool calling และ output tool call JSON เป็น text — แสดง error ที่เข้าใจได้แทน
- fix: ลบ "default" field ออกจาก web_search schema ป้องกัน model บางตัว confused
- fix: เพิ่ม prompt ให้ค้นหาได้สูงสุด 2 ครั้ง และสรุปทันทีหลังค้นหาเสร็จ

---

## [v0.10.0] — 26 มีนาคม 2569 · feat
- feat: web search tool via DDGS (DuckDuckGo) — HR/Accounting/Manager agents สามารถค้นหาข้อมูลอินเทอร์เน็ตได้
- เพิ่ม `_web_search()` function + tool schema `web_search` ใน MCP_TOOLS
- `web_search` อยู่ใน READ_ONLY_TOOLS (ไม่เขียนไฟล์)
- status message แสดง "กำลังค้นหา: {query}..." ระหว่าง streaming
- system prompts ทั้ง 3 agents อัปเดตให้ใช้ web_search เฉพาะข้อมูล real-time เท่านั้น
- เพิ่ม `ddgs` ใน requirements.txt

---

## [v0.9.0] — 25 มีนาคม 2569 · feat
- feat: conversation memory — ส่ง last 10 turns (20 messages) ไปยัง Orchestrator, PM Agent, และ single agents ทุกครั้ง
- Orchestrator ใช้ context ประวัติเพื่อ routing ที่แม่นยำขึ้น (เช่น "เพิ่มงบ" หลัง AI team plan = แก้ไข ไม่ใช่งานใหม่)
- Single agents (HR/Accounting/Manager) เห็น context ก่อนหน้าเพื่อสร้างเอกสารที่ต่อเนื่อง
- Frontend: เก็บ conversationHistory[], push user turn ก่อน fetch, push assistant turn หลัง done event
- Frontend: clear history เมื่อเปลี่ยน workspace (new workspace = new context)
- Backend: sanitize history (max 20 entries, max 3000 chars/entry, role whitelist)

---

## [v0.8.5] — 25 มีนาคม 2569 · fix
- fix: agents อ่านไฟล์ workspace ผิดบริบท — ตัวอย่าง Accounting อ่าน travel expense เก่าแทนที่จะสร้างงบใหม่
- fix: ปรับ system prompts ทั้ง 3 agents ให้อ่านไฟล์เฉพาะเมื่อ user ระบุชื่อไฟล์ หรือขอแก้ไขเอกสารที่มีอยู่โดยตรง
- fix: PM pending state + edit-intent → แจ้งให้ user บันทึก/ยกเลิกก่อน แทนที่จะลบไฟล์ temp โดยไม่แจ้งเตือน

---

## [v0.8.4] — 25 มีนาคม 2569 · feat
- feat: HR/Accounting/Manager agents ใช้ `list_files` + `read_file` ก่อนสร้างเอกสารเพื่อเข้าใจ context ใน workspace
- เพิ่ม `READ_ONLY_TOOLS` — subset ของ MCP_TOOLS สำหรับ single agents (read-only, ไม่มี create/update/delete)
- `run_agent_with_tools` รับ parameter `tools` (default = MCP_TOOLS) ใช้ได้กับทั้ง read-only และ full-access paths
- เพิ่ม tool allow-list enforcement: block tool calls ที่ไม่อยู่ใน allowed set ป้องกัน prompt injection
- อัปเดต system prompt ของ HR/Accounting/Manager ให้ทำ list_files → read_file → สร้างเอกสาร
- status message แยก "กำลังอ่านข้อมูล" vs "กำลังบันทึก" ตาม tool type

---

## [v0.8.3] — 25 มีนาคม 2569 · fix
- fix: sidebar file panel ไม่ refresh หลัง agent save เมื่อ workspace directory ถูกลบแล้วสร้างใหม่
- เพิ่ม global event bus (`_ws_change_queues`) — agent save notify SSE clients โดยตรง ไม่ต้องรอ watchdog
- watchdog ยังทำงานอยู่ (สำหรับ external file changes) แต่ agent save path ผ่าน event bus เสมอ
- fix: cleanup orphaned empty bucket key เมื่อ SSE client disconnect

---

## [v0.8.2] — 25 มีนาคม 2569 · fix
- fix: Orchestrator retry loop — retry API call up to 3 times เมื่อ JSON parse ล้มเหลว ก่อน raise error
- fix: PM Agent retry loop — retry API call up to 3 times เมื่อ JSON parse ล้มเหลว ก่อน raise error
- fix: PM Agent API error ไม่ส่ง str(e) ไปยัง frontend (log server-side แทน)
- แต่ละ retry จะส่ง hint message "ตอบกลับด้วย JSON เท่านั้น" เพื่อ nudge LLM

---

## [v0.8.1] — 25 มีนาคม 2569 · fix
- test_cases.py: เพิ่ม PM Agent test cases (#7, #8) — two-step flow: generate → confirm save
- เพิ่ม routing validation, min_chars check, keyword check สำหรับ cases 1-6
- เพิ่ม PM cases ใน backup/demo-inputs.txt

---

## [v0.8.0] — 25 มีนาคม 2569 · feature
- feature: Workspace Picker Modal — แทนที่ prompt() ด้วย modal แสดง workspace ทั้งหมดแบบคลิกเลือก
- เพิ่ม ALLOWED_WORKSPACE_ROOTS env var — admin กำหนด roots ที่อนุญาต (comma-separated)
- เพิ่ม GET /api/workspaces — scan subdirs ภายใน allowed roots จัดกลุ่มตาม root
- เพิ่ม POST /api/workspace/new — สร้างโฟลเดอร์ใหม่ (validate: a-z/0-9/_/-) + auto-switch
- อัปเดต _is_allowed_workspace_path() ให้ตรวจสอบกับ all allowed roots + realpath symlink-safe
- อัปเดต .env.example เพิ่ม ALLOWED_WORKSPACE_ROOTS example

---

## [v0.7.2] — 25 มีนาคม 2569 · fix
- fix: ลบ format dropdown ออกจาก input-hint-row (ไม่จำเป็นแล้ว เพราะ popup เป็นตัวเลือก format หลัก)
- resolvedFormat ใช้ detectedFormat || pendingFormat || 'md' แทน dropdown value
- pendingFormat ใน single-agent flow ตั้งค่าจาก popup แทน dropdown
- ลบ .format-select CSS และ formatSelect HTML element ออกทั้งหมด

---

## [v0.7.1] — 25 มีนาคม 2569 · fix
- fix: format popup แสดงสำหรับ single-agent doc (HR/Accounting/Manager) ด้วย ไม่ใช่แค่ PM
- เพิ่ม _showSingleFileFormatModal(): แสดง popup 1 row พร้อม agent label + format dropdown
- intercept save intent เมื่อ pendingDoc && pendingAgent → popup ก่อน submit

---

## [v0.7.0] — 25 มีนาคม 2569 · feature
- เพิ่ม file format selector modal: popup แสดง per-file format dropdown ก่อนบันทึก PM files
- เพิ่ม cancel confirm modal: ยืนยันก่อนยกเลิก PM files พร้อมแสดงจำนวนไฟล์
- intercept save/cancel intent ฝั่ง frontend ก่อน submit (ไม่ผ่าน server)
- app.py: handle_pm_save รับ output_formats list (per-file), fallback ไป output_format ถ้าไม่มี
- เพิ่ม _isSaveIntentJS / _isCancelIntentJS สำหรับ PM modal intercept

---

## [v0.6.2] — 25 มีนาคม 2569 · fix
- fix: format detection จาก message text — "save as pdf", "บันทึกเป็น excel" override dropdown
- priority: message keyword → dropdown value (pendingFormat lock ถูกเอาออก)
- dropdown อัปเดตอัตโนมัติเมื่อ detect format จาก message

---

## [v0.6.1] — 25 มีนาคม 2569 · fix
- fix: suppress WeasyPrint/fontTools verbose font subsetting logs (ตั้ง log level ERROR/WARNING)
- fix: _cleanup_old_temp() ข้าม .gitkeep ป้องกันถูกลบทุกครั้งที่ส่ง request

---

## [v0.6.0] — 25 มีนาคม 2569 · feature
- เพิ่ม `converter.py`: แปลง markdown → .txt / .docx / .xlsx / .pdf ที่ save time
- .docx: parse headings, lists, tables, bold ผ่าน python-docx
- .xlsx: ดึง markdown table → openpyxl rows; fallback เนื้อหาทั้งหมดใน A1
- .pdf: markdown → HTML → WeasyPrint พร้อม Thai font (Norasi/Garuda)
- อัปเดต `app.py`: `_suggest_filename` รองรับ extension, `handle_save` และ `handle_pm_save` รับ `output_format`
- อัปเดต `index.html`: format selector dropdown (.md/.txt/.docx/.xlsx/.pdf) ใน input area
- `pendingFormat` lock format ตอน doc pending, restore ผ่าน previousPendingState

---

## [v0.5.2] — 25 มีนาคม 2569 · feature
- อัปเดต `setup.sh`: ติดตั้ง WeasyPrint system libs อัตโนมัติ (libpango, libharfbuzz, libffi, libjpeg, libopenjp2, fonts-thai-tlwg)
- เพิ่ม library verify step ใน setup.sh (ตรวจสอบ flask, openai, docx, openpyxl, weasyprint, markdown)
- อัปเดต `requirements.txt`: เพิ่ม python-docx, openpyxl, weasyprint, markdown

---

## [v0.5.1] — 25 มีนาคม 2569 · feature
- เพิ่ม `history.html` — หน้าดูประวัติ job แบบ standalone (dark theme เดียวกับ main UI)
- Stats bar: job ทั้งหมด, สำเร็จ, ไฟล์บันทึก, error
- Job card: agent badge, status dot, truncated input, วันที่
- คลิก card เพื่อ expand: แสดง output text (markdown rendered) + file chips
- เพิ่ม Flask route `/history` เสิร์ฟ `history.html`
- Back button กลับหน้าหลัก

---

## [v0.5.0] — 25 มีนาคม 2569 · feature
- เพิ่ม SQLite persistence layer (`db.py`) — บันทึกทุก job, agent routing, output text, และไฟล์ที่ save
- DB schema: 2 ตาราง (`jobs`, `saved_files`) พร้อม WAL mode + foreign keys + index
- Graceful degradation: DB error ไม่กระทบ chat flow — ถ้า DB ใช้ไม่ได้ระบบยังทำงานปกติ
- Zombie job cleanup: job ที่ค้าง `pending` เกิน 1 ชั่วโมงถูก mark เป็น `error` อัตโนมัติทุก startup
- เพิ่ม `session_id` (localStorage UUID) ส่งมากับทุก request เพื่อเตรียมรองรับ auth
- เพิ่ม `/api/history` และ `/api/history/<job_id>` routes
- อัปเดต `/api/health` ให้รายงานสถานะ DB
- เพิ่ม `data/` directory (gitignored) สำหรับเก็บ `assistant.db`
- Prototype phase เริ่มต้น: v0.5.x

---

## [v0.4.21] — 24 มีนาคม 2569 · fix
- เพิ่ม `start.sh` และ `setup.sh` สำหรับรัน app บน WSL โดยตรง
- เปลี่ยน Flask host เป็น `0.0.0.0` (configurable ด้วย `FLASK_HOST`) เพื่อให้เข้าถึงได้จาก Windows browser ผ่าน WSL
- อัปเดต CORS origins รองรับการเข้าถึงผ่าน WSL network
- แก้ Python 3.10 SyntaxError: backslash ใน nested f-string expression

---

## [v0.4.20]
---

## [v0.4.12] — 24 มีนาคม 2569 · fix
- เพิ่ม `smoke_test_phase0.py` เพื่อตรวจ Phase 0 hardening ด้วย Python stdlib (`urllib`) โดยไม่พึ่ง `requests`
- ทำให้ smoke test คำยืนยันภาษาไทย (`บันทึก` / `ยกเลิก`) ไม่ให้ได้ false negative จาก Windows shell encoding โดยใช้ UTF-8 JSON และ Unicode escape
- เพิ่ม retry แบบแคบๆ สำหรับ `basic chat` และจับ transport timeout/error ให้สคริปต์รายงาน FAIL พร้อมสาเหตุแทนการ crash
- อัปเดตเอกสารที่เกี่ยวข้องให้สะท้อน root cause ของ false alarm และวิธีรัน smoke test ที่ถูกต้องบน Windows

---

## [v0.4.11] — 24 มีนาคม 2569 · fix
- ลด XSS risk ฝั่ง frontend โดยเปลี่ยนการ render ข้อมูลจาก server/LLM หลายจุดไปใช้ DOM API แทน `innerHTML`
- sanitize markdown output ก่อนแทรกกลับเข้า DOM
- harden file list, agent badge, PM plan, tool result, และ error rendering ให้ปลอดภัยขึ้น

---

## [v0.4.10] — 24 มีนาคม 2569 · fix
- แยกกรณี `save_failed` ออกจาก success path ของการบันทึกไฟล์ฝั่ง single-agent
- ป้องกันการแสดงข้อความสำเร็จปลอมเมื่อ `create_file` ล้มเหลว
- คง pending confirmation state เดิมใน frontend เมื่อการบันทึกล้มเหลวหรือ request ยืนยันสะดุด

---

## [v0.4.9] — 24 มีนาคม 2569 · fix
- จำกัดการเปลี่ยน workspace ผ่าน `POST /api/workspace` ให้อยู่ภายใต้ root ของโปรเจกต์เท่านั้น
- คงรูปแบบ API เดิมไว้เพื่อลดผลกระทบกับ frontend ที่มีอยู่
- อัปเดตเอกสารให้สะท้อนข้อจำกัดใหม่ของ workspace selector/runtime

---

## [v0.4.8] — 24 มีนาคม 2569 · fix
- ปิด Flask debug mode เป็นค่าเริ่มต้นสำหรับการรันปกติ
- เพิ่มการเปิด debug ผ่าน environment variable `FLASK_DEBUG=1` แทนการ hardcode ใน `app.py`
- อัปเดตเอกสาร setup/runtime ให้ตรงกับพฤติกรรมใหม่ของ backend

---

## [v0.4.7] — 24 มีนาคม 2569 · fix
- **`_is_edit_intent()`**: เพิ่ม keyword set สำหรับคำสั่งแก้ไข (แก้ไข, ปรับ, เพิ่ม, ลบ, เปลี่ยน, edit, modify ฯลฯ)
- Single-agent pending block ตรวจสอบ 4 cases ชัดเจน: save → บันทึก / discard → ยกเลิก / edit intent → revise / **อื่นๆ = งานใหม่ → fall through Orchestrator**
- แก้ปัญหา: ส่งงานใหม่ขณะ pending → agent เดิมถูกเรียกแทน Orchestrator เลือกใหม่

---

## [v0.4.6] — 24 มีนาคม 2569 · fix
- **Fall-through routing**: เมื่อ user ส่งงานใหม่ขณะมี pending state → ยกเลิกไฟล์เดิมแล้ว **ส่งงานใหม่ไปยัง Orchestrator ต่อ** (ไม่ตัดจบอีกต่อไป)
- เพิ่ม `_is_pure_discard()` helper — ตรวจสอบว่า message เป็นแค่ keyword ยกเลิกล้วนๆ (exact match) ไม่ใช่ substring
- PM pending block: save → done+return / pure discard → confirm+done+return / งานใหม่ → แจ้ง "ยกเลิกแล้ว" แล้ว **fall through ไปยัง Orchestrator**
- Single-agent pending block: เพิ่ม branch เดียวกัน — pure discard → stop, discard+งานใหม่ → fall through

---

## [v0.4.5] — 24 มีนาคม 2569 · fix
- **✕ ยกเลิก button**: ปรากฏใต้ input เฉพาะเมื่ออยู่ใน confirmation state — คลิกเพื่อ clear pending state ทันที (client-side, ไม่ต้องส่ง request)
- **Discard keywords backend**: เพิ่ม `_is_discard_intent()` — ตรวจจับ "ยกเลิก", "cancel", "งานใหม่" ฯลฯ ใน single-agent pending flow
- แก้ bug: ส่งงานใหม่ขณะมี pending doc → ถูกตีความเป็น edit แทน → ตอนนี้กด ✕ หรือพิมพ์ "ยกเลิก" เพื่อ clear แล้วส่งงานใหม่ผ่าน Orchestrator ได้
- Hint text ปรับเป็น "💬 พิมพ์ บันทึก หรือ ✏️ ระบุสิ่งที่แก้ไข" ชัดเจนขึ้น

---

## [v0.4.4] — 24 มีนาคม 2569 · fix
- **PM Agent max_tokens**: เพิ่มจาก 1024 → 6000 — แก้ปัญหา subtask JSON ถูกตัดกลางคัน
  (1024 ไม่เพียงพอเมื่อ task descriptions ยาวแบบ self-contained)
- เพิ่ม `finish_reason` logging สำหรับ Orchestrator และ PM Agent
  เพื่อตรวจจับการ truncation ในอนาคต (warning เมื่อ finish_reason == 'length')

---

## [v0.4.3] — 24 มีนาคม 2569 · feat
- **Temp staging flow**: PM subtasks ใช้ `stream_agent()` แทน `run_agent_with_tools()` — stream เนื้อหาเต็มให้ user เห็น real-time
- **Temp directory**: `temp/` staging area — ไฟล์รอ confirm ที่นี่ ไม่ปรากฏใน workspace/file panel
- `_write_temp()` + `_move_to_workspace()` helpers — `os.replace()` atomic move
- `_cleanup_old_temp()` — ลบ temp files เก่ากว่า 1 ชั่วโมงอัตโนมัติ
- `handle_pm_save()` — รับ `pending_temp_paths[]` → move ทุกไฟล์ไปยัง workspace
- **PM confirmation flow**: หลัง PM tasks เสร็จ → hint "💾 พิมพ์ บันทึก เพื่อบันทึก N ไฟล์"
- Frontend: `pendingTempPaths[]` + `pending_file` SSE event + `_updateInputHint(isPending, fileCount)`

---

## [v0.4.2] — 23 มีนาคม 2569 · fix
- **PM Agent JSON parse**: เพิ่ม `_extract_json()` helper — strip code fences (ทุก variant), slice `{...}` จาก LLM output ก่อน parse
- **PM_PROMPT hardened**: เปิด prompt ด้วย OUTPUT FORMAT — CRITICAL, ห้าม code fences ซ้ำท้าย prompt
- **Orchestrator JSON parse**: ใช้ `_extract_json()` แทน inline replace chain
- **Subtask validation**: filter subtasks ที่ `agent` ไม่ใช่ hr/accounting/manager ออกก่อน execute
- **Sidebar badge overflow**: เพิ่ม `max-height: 96px`, `overflow: hidden`, `word-break: break-word` ใน `.agent-badge`
- **Badge reason clamp**: เพิ่ม `.agent-badge-reason` class (2-line clamp) แทน inline style

---

## [v0.4.1] — 23 มีนาคม 2569 · feat
- Confirmation flow (frontend): AI generates document → asks for edit or save → user types "บันทึก" or edit instruction
- State tracking: `pendingDoc`, `pendingAgent`, `isPendingConfirmation`, `wasPMTask`, `lastAgent`
- Input hint ไฮไลท์เป็นสีหลักเมื่ออยู่ใน confirmation state: "💬 พิมพ์ บันทึก เพื่อบันทึกไฟล์ หรือระบุสิ่งที่ต้องการแก้ไข"
- ส่ง `pending_doc` + `pending_agent` ไปกับ request ถัดไปเมื่ออยู่ใน pending state
- PM task ไม่เข้า pending flow (auto-save คงเดิม)

---

## [v0.4.0] — 23 มีนาคม 2569 · feat (Minor)
- **PM Agent**: แตก task ที่ครอบคลุมหลาย domain ออกเป็น subtasks พร้อมกำหนด Agent ที่เหมาะสม
- **MCP Filesystem**: Python FastMCP server + 5 tools (create/read/update/delete/list files)
- **Agentic Loop**: LLM → tool_calls → execute → feed back → repeat (max 5 รอบ) สำหรับทุก agent
- **Workspace Selector**: เลือก directory ได้ใน navbar, กำหนดขอบเขตการทำงานของ agent
- **Real-time File Panel**: sidebar แสดงไฟล์ใน workspace แบบ live (SSE + watchdog)
- **New endpoints**: GET/POST /api/workspace, GET /api/files, GET /api/files/stream
- Path traversal prevention: agent ออกนอก workspace ไม่ได้

---

## [v0.3.9] — 23 มีนาคม 2569 · feat
- Chat bubble UI: user message แสดงเป็น bubble ขวา, AI response แสดงซ้าย
- ประวัติสนทนาสะสมใน chat log (ไม่ clear ทุก send)
- สร้าง DOM elements ใหม่ต่อทุก message (`.msg-user`, `.msg-ai-container`, `.msg-ai-body`)
- `copyOutput()` copy จาก AI bubble ล่าสุด (`.output-area` สุดท้าย)
- แทน static `#outputContainer` ด้วย dynamic `.chat-log#chatLog`

---

## [v0.3.8] — 23 มีนาคม 2569 · fix
- แก้ status bar: "tokens" → "ตัวอักษร" (ตัวเลขที่แสดงคือจำนวนตัวอักษร ไม่ใช่ API tokens)
- แก้ typing indicator ค้างเมื่อเกิด error: ซ่อน typing dots และลบ class `.typing` ทั้งใน SSE error event และ catch block

---

## [v0.3.7] — 23 มีนาคม 2569 · fix
- ai-accent-line สูงพอดีกับ typing bubble ระหว่าง typing state (`.output-container.typing` class)
- เส้นยังยืดตาม text เหมือนเดิมเมื่อ streaming เริ่ม

---

## [v0.3.6] — 23 มีนาคม 2569 · feat
- Typing indicator: 3 จุดเด้งใน output area ระหว่างรอ agent ตอบกลับ (เหมือน chat bubble)
- แสดงเมื่อ `agent` event มาถึง → ซ่อนเมื่อข้อความแรกเริ่ม stream
- CSS `@keyframes typing-bounce` + `.typing-indicator` พร้อม stagger delay

---

## [v0.3.5] — 23 มีนาคม 2569 · feat
- Nav-items เปลี่ยนเป็น pill chips (flex-wrap, border-radius: 99px, border)
- Hover: background + primary border แทน slide animation
- Dark mode สว่างขึ้น: bg #0B0E14→#13171f, surface #151921→#1b2130
- Secondary text สว่างขึ้น: --on-surface-2 #abb3b7→#c8d2d8

---

## [v0.3.4] — 23 มีนาคม 2569 · fix
- Sidebar Agent badge: reserved space ตลอดเวลา (ไม่ใช้ display:none อีกต่อไป)
- Idle state แสดง "รอคำสั่งงาน..." พร้อม dashed border จาง
- ตัวอย่างงานไม่ขยับขึ้นลงอีกไม่ว่า agent จะ active หรือไม่

---

## [v0.3.3] — 23 มีนาคม 2569 · feat
- Input area redesign: button ย้ายเข้าไปอยู่ใน container (absolute bottom-right) สไตล์ ChatGPT/Claude
- เพิ่ม `.input-wrapper` (backdrop-filter blur) + `.input-container` (position: relative, border-radius: 20px)
- textarea: padding-right: 52px ป้องกันข้อความทับปุ่ม, max-height 200px
- send button: gradient background, opacity transition
- เพิ่ม input-hint "INTERNAL POC · DRAFT OUTPUT ONLY" ด้านล่าง input box

---

## [v0.3.2] — 23 มีนาคม 2569 · feat
- Auto-resize textarea: เริ่มต้น 1 บรรทัด → ขยายตาม content (max 5 บรรทัด / 140px)
- Reset กลับ 1 บรรทัดอัตโนมัติหลัง send
- fillInput() (nav-item click) trigger resize ด้วย

---

## [v0.3.1] — 23 มีนาคม 2569 · feat
- เพิ่ม Markdown rendering ด้วย marked.js (CDN)
- ระหว่าง streaming แสดงเป็น plain text — switch เป็น rendered HTML ตอน done
- เพิ่ม CSS สำหรับ markdown elements: h1-h3, table, code, blockquote, ul/ol, hr
- แก้ status-row พื้นหลังทึบ (`background: var(--bg)`) ป้องกัน text ทับกันเมื่อ scroll

---

## [v0.3.0] — 23 มีนาคม 2569 · feat
**UI Redesign — "The Silent Concierge"**
- ออกแบบ UI ใหม่ทั้งหมดตาม design system "High-End Editorial"
- เพิ่ม fixed Navbar (frosted glass, app title, version tag)
- ออกแบบ Sidebar ใหม่: Material Symbols icons, slide hover effect, model pill ใน footer
- Floating input-footer พร้อม gradient fade และ rounded input-box
- AI accent line (primary color) ปรากฏระหว่าง streaming ด้วย `.streaming` CSS class
- CSS Custom Properties สำหรับ dark/light mode (dark default) ผ่าน `body.light-mode`
- ฟอนต์: Inter + Sarabun + Material Symbols Outlined
- ทุก JS logic เดิมยังคงสมบูรณ์ (SSE, copy, timer, modelName, theme toggle)

---

## [v0.2.3] — 23 มีนาคม 2569 · docs
- เพิ่ม PROJECT_SUMMARY.md — ภาพรวมทั้งโปรเจกต์สำหรับ onboard AI ในการสนทนาใหม่
- ครอบคลุม: architecture, agents, file structure, run commands, version history, rules

รูปแบบ: [v0.MINOR.PATCH] — วันที่ · ประเภท · รายละเอียด

---

## [v0.2.2] — 23 มีนาคม 2569 · chore
- เปลี่ยนรูปแบบ version เป็น semantic versioning (v0.MINOR.PATCH)
- เพิ่มกฎ versioning ใน CLAUDE.md พร้อม version history

## [v0.2.1] — 23 มีนาคม 2569 · fix
- แก้ bug: Agent badge แสดง "Accounting Agent" แทน "Manager Advisor"
- เพิ่ม CSS class `agent-manager` สีม่วง (dark + light mode)
- แก้ sidebar footer: เพิ่ม Manager ในรายการ agents

## [v0.2.0] — 23 มีนาคม 2569 · feat
**Manager Advisor Agent (ใหม่)**
- เพิ่ม `MANAGER_PROMPT`: เชี่ยวชาญการบริหารทีมสำหรับ Team Lead
  - ครอบคลุม: Feedback, budget, ลำดับความสำคัญ, ความขัดแย้งในทีม, headcount
  - ให้ Script คำพูดจริงสำหรับการ feedback พนักงาน
  - ผลลัพธ์ทำได้ภายใน 48 ชั่วโมง
- อัปเดต Orchestrator: รองรับ routing 3 agents (hr / accounting / manager)
- อัปเดต generate(): system_prompt, agent_label, agent_max_tokens สำหรับ manager

**UI Improvements**
- เพิ่ม Processing time counter: "✅ เสร็จสิ้น · X.X วินาที · X,XXX tokens"
- เพิ่มปุ่ม Copy to clipboard (แสดงหลัง done event)

## [v0.1.0] — 23 มีนาคม 2569 · feat (initial)
**Core System**
- Flask backend + SSE streaming (Server-Sent Events)
- Multi-agent routing: Orchestrator → HR Agent / Accounting Agent
- OpenAI SDK เชื่อมต่อ OpenRouter API
- Model กำหนดผ่าน `OPENROUTER_MODEL` env var (ไม่ต้องแก้ code)

**HR Agent**
- สัญญาจ้างพนักงาน (ตามกฎหมายแรงงานไทย)
- Job Description
- อีเมลแจ้งนโยบายพนักงาน

**Accounting Agent**
- Invoice / ใบกำกับภาษี (พร้อม VAT 7%, เลขผู้เสียภาษี)
- สรุปค่าใช้จ่าย (ไม่มี VAT)
- ใช้วันที่ พ.ศ. 2569

**Frontend**
- Dark mode default, toggle light/dark พร้อม localStorage
- Enter ส่ง, Shift+Enter ขึ้นบรรทัดใหม่
- Agent badge แสดงสีตาม agent (green=HR, purple=Accounting)
- Model name ดึงจาก `/api/health` อัตโนมัติ

**Error Handling**
- Input validation (max 5,000 ตัวอักษร)
- API errors: RateLimitError, APITimeoutError, APIError
- Generic error message ภาษาไทย (ไม่ leak technical details)

---

_ทุก version มี AI disclaimer ท้ายเอกสาร: "⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง"_
# Unreleased

- fix: add session deletion from the Next.js sidebar with a matching backend API
- fix: refresh the Next.js session list immediately after sending and completing chat messages
- fix: add a top navbar and a new-session button to reset the Next.js chat view
- fix: make the Next.js empty-state quick actions clickable
- fix: render assistant messages progressively while SSE text is streaming
- fix: reduce perceived delay when switching sessions with immediate highlight, cache, and loading state
- feat: redesign the Next.js interface with a cleaner layout and persistent light/dark theme toggle
- fix: tighten header controls and reduce empty-state panel sizing for better spacing
- fix: correct the redesigned header theme toggle sizing so the knob stays inside the switch
- fix: make the workspace selection modal fully opaque with a stronger backdrop
- fix: restore the Next.js save flow so save intents open the format picker and refresh saved files
- fix: allow the selected session to restore its messages again when the chat view was cleared locally
- fix: make the save-format modal fully opaque with a stronger backdrop
- fix: prevent the active session cache from overwriting saved history with an empty chat snapshot
- fix: harden backend job status tracking and request validation for revise, PM, orchestrator, and history flows
- fix: harden shared client/session state and file-stream SSE against races and leaks
