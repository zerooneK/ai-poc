# Changelog — Internal AI Assistant POC

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
