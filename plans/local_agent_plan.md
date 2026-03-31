# Project Plan: Local File Agent

**Goal:** ให้ AI agents สามารถสร้าง/แก้ไข/ลบไฟล์บนเครื่อง local ของ user ผ่าน browser เป็นตัวกลาง โดยมี sandbox ป้องกันการออกนอก directory ที่กำหนด และ fallback กลับ server-side เมื่อ local agent ไม่รัน

**Scope:**
- รวม: `local_agent.py` (HTTP server), การแก้ `index.html` (detection + proxy), optional tray icon wrapper
- ไม่รวม: authentication ระหว่าง browser กับ local agent, HTTPS, sync สองทิศทางระหว่าง server workspace กับ local folder, mobile browser support

**Tech Stack:** Python 3.10+ (http.server / Flask-lite), vanilla JS (fetch + ReadableStream), Windows 10/11

**Scale Target:** 1 user / 1 browser session — ไม่ต้องรองรับ concurrent users บน local agent

**Estimated Effort:** 4–6 วันทำงาน (Medium confidence — ขึ้นกับ CORS edge case บน Windows browser)

**Plan Version:** 1.0 | **Date:** 27 มีนาคม 2569

**Version Target ภาพรวม:**

| Phase | Version | Deliverable |
|-------|---------|-------------|
| Phase 1 | v0.22.0 | `local_agent.py` — HTTP server พร้อม sandbox + CORS |
| Phase 2 | v0.23.0 | `index.html` — detection + proxy file ops ไป localhost:7000 |
| Phase 3 | v0.24.0 | UI: directory picker + status indicator ใน sidebar |
| Phase 4 | v0.25.0 | Optional: `local_agent_tray.py` — pystray wrapper |

---

## Summary Table

| Task | Phase | Owner | Version | Est. Time | Depends On |
|------|-------|-------|---------|-----------|------------|
| T1.1 | 1 | backend-developer | v0.22.0 | 3h | — |
| T1.2 | 1 | backend-developer | v0.22.0 | 2h | T1.1 |
| T1.3 | 1 | backend-developer | v0.22.0 | 2h | T1.2 |
| T1.4 | 1 | backend-python-reviewer | v0.22.0 | 1h | T1.3 |
| T2.1 | 2 | frontend-developer | v0.23.0 | 2h | T1.3 |
| T2.2 | 2 | frontend-developer | v0.23.0 | 3h | T2.1 |
| T2.3 | 2 | frontend-developer | v0.23.0 | 2h | T2.2 |
| T2.4 | 2 | ui-ux-reviewer | v0.23.0 | 1h | T2.3 |
| T3.1 | 3 | frontend-developer | v0.24.0 | 3h | T2.3 |
| T3.2 | 3 | frontend-developer | v0.24.0 | 2h | T3.1 |
| T4.1 | 4 | backend-developer | v0.25.0 | 3h | T1.3 |
| T4.2 | 4 | backend-developer | v0.25.0 | 2h | T4.1 |

---

## Work Breakdown Structure (WBS)

---

### Phase 1 — local_agent.py: HTTP Server + Sandbox | 7h | สร้าง local HTTP server ที่ทำงานบนเครื่อง user พร้อม path sandbox

**Phase Exit Criteria:**
- `local_agent.py` รันได้บน Windows โดยไม่ต้องติดตั้ง dependency นอก stdlib
- ทุก endpoint ผ่าน smoke test ด้วย `curl` หรือ browser devtools
- Path traversal ทุกรูปแบบถูก reject ด้วย 400 ก่อนแตะ filesystem จริง
- CORS header ตอบกลับ `http://localhost:5000` และ `http://127.0.0.1:5000` เท่านั้น

---

#### Task T1.1: สร้าง local_agent.py — HTTP server skeleton พร้อม CORS

**Type:** Feature
**Assigned To:** backend-developer
**Estimated Time:** 3h
**Depends On:** none

**Description**

สร้างไฟล์ `local_agent.py` ที่ root ของ project โดยใช้ `http.server.BaseHTTPRequestHandler` (Python stdlib เท่านั้น ไม่ต้อง pip install) เปิด port 7000 ด้วย `socketserver.TCPServer`. Handler ต้องตอบ CORS preflight `OPTIONS` ด้วย header ที่ถูกต้อง และมี `GET /health` endpoint ที่ตอบ `{"status":"ok","sandbox":"<path>"}` เพื่อให้ browser ใช้ตรวจสอบว่า agent รันอยู่

Port 7000 ต้องอ่านได้จาก environment variable `LOCAL_AGENT_PORT` โดย default คือ 7000 หาก port ถูก occupy ต้อง print error message ที่อ่านได้ก่อน exit แทนที่จะ crash ด้วย traceback ที่ไม่เป็นมิตร

**Evidence จาก codebase:** `app.py` line 333 ใช้ `CORS(app, origins=["http://localhost:5000", ...])` — เราต้องเลียนแบบ allowlist เดียวกันบน local agent เพื่อให้ browser ยอมรับ cross-origin request จาก `http://localhost:5000` ไปยัง `http://localhost:7000`

**Acceptance Checklist**
- [ ] `python local_agent.py` รันได้บน Windows CMD และ PowerShell โดยไม่มี import error
- [ ] `GET http://localhost:7000/health` ตอบ `{"status":"ok","sandbox":"<path>"}` ภายใน 200ms
- [ ] `OPTIONS http://localhost:7000/health` ตอบ `200` พร้อม `Access-Control-Allow-Origin: http://localhost:5000`
- [ ] เมื่อ port ถูก occupy ให้แสดง `[LocalAgent] ERROR: port 7000 is already in use` แล้ว exit code 1
- [ ] Port อ่านได้จาก `LOCAL_AGENT_PORT` env var
- [ ] ไม่มี dependency นอก Python stdlib

**Definition of Done**
```
DONE when:
  - ทุก checklist ข้างต้นผ่าน
  - ทดสอบบน Windows 11 จริง (ไม่ใช่แค่ WSL)
  - Code reviewed โดย backend-python-reviewer
  - ไม่มี hardcoded origin string — อ่านจาก ALLOWED_ORIGINS env var หรือ constant ที่ define ครั้งเดียว

NOT DONE if:
  - CORS header ส่งทุก origin โดยไม่มี allowlist
  - รันได้ใน WSL แต่ไม่ได้ทดสอบใน Windows CMD
  - Port hardcode เป็น 7000 ใน 2 ที่ขึ้นไป
```

**Fallback Plan**
```
If stdlib http.server ไม่รองรับ chunked/SSE หรือ OPTIONS handling พัง:
  Fallback: ใช้ Flask (ซึ่ง project มีอยู่แล้วใน requirements.txt) แทน stdlib
  Trade-off: user ต้อง pip install (แต่ project มี venv อยู่แล้ว — รันด้วย ./venv/bin/python local_agent.py)
  Trigger: OPTIONS test ล้มเหลวบน Chrome Windows หลังลอง 3 วิธีกับ stdlib แล้ว
  Decision Owner: backend-developer
```

**Scaling Consideration**
```
Current: 1 user, 1 browser tab
Bottleneck at: N/A — single-user by design
Mitigation: TCPServer(allow_reuse_address=True) ป้องกัน TIME_WAIT crash เมื่อ restart
Future-safe: Yes — port configurable, ไม่มี shared state
```

**Maintainability Note**
ให้ define CORS allowed origins เป็น module-level constant `ALLOWED_ORIGINS` แทน hardcode ในทุก handler method เพื่อให้แก้ได้ใน 1 จุด

---

#### Task T1.2: Implement path sandbox — _validate_path() port สำหรับ local agent

**Type:** Feature
**Assigned To:** backend-developer
**Estimated Time:** 2h
**Depends On:** T1.1

**Description**

Copy logic ของ `_validate_path(workspace, filename)` จาก `mcp_server.py` มาใช้ใน `local_agent.py` โดยตรง (ไม่ import) เพื่อให้ local_agent เป็น standalone script ที่ไม่มี server-side dependency ความแตกต่างคือ sandbox path ต้องอ่านจาก CLI argument `--sandbox-dir` หรือ environment variable `LOCAL_AGENT_SANDBOX` และต้อง resolve เป็น absolute path ตอน startup

Sandbox path ต้อง exist ก่อน server จะ start — ถ้าไม่ exist ให้ print error และ exit 1 แทนสร้างอัตโนมัติ (เพราะ user ต้องเลือกจงใจ ไม่ใช่ให้ script สร้างให้โดยไม่รู้ตัว)

**Evidence จาก codebase:** `mcp_server.py` lines 14–25 — `_validate_path()` ใช้ `os.path.commonpath()` เทียบ resolved path กับ workspace_abs ซึ่งเป็น approach ที่ถูกต้องแล้ว ให้ port เหมือนกันทุก character อย่าเขียนใหม่

```python
# Pattern จาก mcp_server.py ที่ต้อง port มา (อย่าแก้ logic)
def _validate_path(sandbox: str, filename: str) -> str:
    sandbox_abs = str(Path(sandbox).resolve())
    target = str(Path(sandbox_abs, filename).resolve())
    try:
        common = os.path.commonpath([sandbox_abs, target])
        if common != sandbox_abs:
            raise ValueError(f"ไม่อนุญาต: '{filename}' อยู่นอก sandbox")
    except ValueError:
        raise ValueError(f"ไม่อนุญาต: '{filename}' อยู่นอก sandbox")
    return target
```

**Acceptance Checklist**
- [ ] `../etc/passwd` ถูก reject ด้วย ValueError ก่อนแตะ filesystem
- [ ] `../../Windows/System32/calc.exe` ถูก reject
- [ ] `subdir/file.txt` (nested) ผ่านถ้า subdir อยู่ใน sandbox
- [ ] Path ที่มี null byte (`\x00`) ถูก reject (Python's open() reject เองแล้ว แต่ validate ก่อน)
- [ ] Symlink ที่ชี้ออกนอก sandbox ถูก reject (Path.resolve() unroll symlinks)
- [ ] Startup log แสดง `[LocalAgent] Sandbox: <absolute_path>`
- [ ] ถ้า sandbox dir ไม่ exist ให้ exit 1 พร้อม error message ภาษาไทย/อังกฤษ

**Definition of Done**
```
DONE when:
  - Unit test ครอบคลุม path traversal ทุก case ข้างต้นผ่าน
  - ทดสอบด้วย Windows path separator (`\`) ด้วย ไม่ใช่แค่ Unix
  - Reviewed โดย backend-python-reviewer (security-sensitive code)
  - Logic เหมือน mcp_server.py ทุก character — ไม่มี divergence

NOT DONE if:
  - Logic ต่างจาก mcp_server._validate_path() โดยไม่มีเหตุผล
  - ไม่มี test สำหรับ Windows backslash path
  - Sandbox path resolve ตอน request แทนตอน startup
```

**Fallback Plan**
```
If Windows path edge case (drive letter, UNC path) ทำให้ commonpath() พัง:
  Fallback: เพิ่ม pre-check ด้วย os.path.abspath() + str.startswith() เป็น defense-in-depth ก่อน commonpath
  Trade-off: double validation แต่ปลอดภัยกว่า
  Trigger: test กับ path C:\Users\..\Windows\ แล้ว commonpath() ไม่ throw
  Decision Owner: backend-developer
```

**Scaling Consideration**
```
Current: validate ทุก request — cheap operation (no I/O)
Bottleneck at: N/A
Mitigation: ไม่มี — Path.resolve() เร็วมาก
Future-safe: Yes
```

**Maintainability Note**
ให้ function signature เหมือน `mcp_server._validate_path(workspace, filename)` ทุกประการ เพื่อให้ใช้ unit test เดียวกันทดสอบได้ทั้งสอง module

---

#### Task T1.3: Implement file operation endpoints

**Type:** Feature
**Assigned To:** backend-developer
**Estimated Time:** 2h
**Depends On:** T1.2

**Description**

Implement 5 endpoints ใน local_agent.py ที่ mirror `mcp_server.py` ทุก operation:

| Method | Path | Operation | Body |
|--------|------|-----------|------|
| POST | /files/create | สร้างไฟล์ใหม่ | `{"filename":"...", "content":"..."}` |
| POST | /files/read | อ่านไฟล์ | `{"filename":"..."}` |
| POST | /files/update | เขียนทับไฟล์ | `{"filename":"...", "content":"..."}` |
| POST | /files/delete | ลบไฟล์ | `{"filename":"..."}` |
| GET | /files/list | แสดงรายการ | — |

Response format ต้องสม่ำเสมอ:
- Success: `{"ok": true, "result": "<message>"}`
- Error: `{"ok": false, "error": "<message>"}` พร้อม HTTP status ที่เหมาะสม (400 สำหรับ path traversal, 404 สำหรับไฟล์ไม่พบ, 409 สำหรับ file exists)

**Evidence จาก codebase:** `app.py` line 187 ใช้ `_tool_result_is_error()` ตรวจ string ที่ขึ้นต้นด้วย `❌` — local agent ควรใช้ structured JSON แทนเพื่อให้ browser-side แยก success/error ได้โดยไม่ต้อง parse emoji

**Acceptance Checklist**
- [ ] POST /files/create ด้วย filename ที่มี path traversal ตอบ `400 {"ok":false,"error":"..."}`
- [ ] POST /files/create ด้วยไฟล์ที่มีอยู่แล้ว ตอบ `409 {"ok":false,"error":"..."}`
- [ ] POST /files/read ด้วยไฟล์ที่ไม่มี ตอบ `404 {"ok":false,"error":"..."}`
- [ ] POST /files/update ด้วยไฟล์ที่ไม่มี ตอบ `404 {"ok":false,"error":"..."}`
- [ ] GET /files/list ตอบ `200 {"ok":true,"result":[{"name":"...","size":0,"modified":"..."}]}`
- [ ] Content ที่มี Thai characters อ่าน/เขียนถูกต้อง (UTF-8)
- [ ] CORS header มีในทุก response (ไม่ใช่แค่ OPTIONS)
- [ ] Request body ที่ไม่ใช่ JSON ตอบ `400` ไม่ crash

**Definition of Done**
```
DONE when:
  - ทุก endpoint ผ่าน smoke test ด้วย curl จาก Windows CMD
  - Thai content roundtrip (write แล้ว read กลับมาได้ครบ) ผ่าน
  - Error response มี HTTP status code ที่ถูกต้องทุก case
  - Reviewed โดย backend-python-reviewer
  - ไม่มี bare except — ทุก except ระบุ exception type

NOT DONE if:
  - Error response ทั้งหมด return 500 โดยไม่แยก type
  - ไม่มี CORS header ใน non-OPTIONS response
  - Thai filename เก็บได้แต่อ่านกลับมา garbled
```

**Fallback Plan**
```
If stdlib BaseHTTPRequestHandler ยากเกินไปในการ route และ parse JSON body:
  Fallback: ใช้ Flask minimal app แทน (เพิ่ม dependency แต่โค้ดสั้นและอ่านง่ายกว่ามาก)
  Trade-off: user ต้อง activate venv ก่อนรัน แต่สามารถเขียน batch script ให้ได้
  Trigger: LOC ของ stdlib handler เกิน 200 บรรทัด หรือ OPTIONS preflight ไม่ทำงานบน Chrome
  Decision Owner: backend-developer — ต้องตัดสินใจก่อน implement T2.1
```

**Scaling Consideration**
```
Current: sequential request handling (stdlib TCPServer เป็น single-threaded โดย default)
Bottleneck at: ถ้า browser ส่ง concurrent requests พร้อมกัน (เช่น PM mode สร้าง 3 ไฟล์) อาจ queue
Mitigation: ใช้ ThreadingMixIn หรือ socketserver.ThreadingTCPServer แทน TCPServer
Future-safe: Yes — เปลี่ยน server class ได้โดยไม่แก้ handler logic
```

**Maintainability Note**
แยก handler logic ออกจาก routing — สร้าง `_handle_create()`, `_handle_read()` ฯลฯ เป็น method แยก เพื่อให้ test แต่ละ operation ได้โดยไม่ต้อง mock HTTP server ทั้งหมด

---

#### Task T1.4: Code review + unit test สำหรับ local_agent.py

**Type:** Testing
**Assigned To:** backend-python-reviewer
**Estimated Time:** 1h
**Depends On:** T1.3

**Description**

รัน `backend-python-reviewer` subagent ตาม mandatory review order ใน CLAUDE.md รีวิว `local_agent.py` ทั้งไฟล์ก่อน commit version v0.22.0 เน้นตรวจ: path traversal bypass, CORS misconfiguration, bare except, hardcoded values, และ Windows path compatibility

**Acceptance Checklist**
- [ ] backend-python-reviewer ผ่านโดยไม่มี HIGH severity issue
- [ ] Path traversal test ครบ 5 รูปแบบ (relative, absolute, symlink, null byte, Windows UNC)
- [ ] ไม่มี `except Exception` หรือ bare `except:` โดยไม่มี justification
- [ ] ไม่มี secret หรือ path ของ developer ใน code
- [ ] CHANGELOG.md อัปเดตเป็น v0.22.0

**Definition of Done**
```
DONE when:
  - backend-python-reviewer report ไม่มี item ที่ block commit
  - v0.22.0 commit สร้างแล้วพร้อม CHANGELOG entry
  - local_agent.py รันได้บน Windows 11 จริง (ไม่ใช่แค่ WSL)
```

---

### Phase 2 — index.html: Detection + File Operation Proxy | 7h | Browser ตรวจจับ local agent และ route file ops ไป localhost:7000 แทน server

**Phase Exit Criteria:**
- เมื่อ local agent รัน: AI สร้างไฟล์บนเครื่อง user จริง (ตรวจได้จาก File Explorer)
- เมื่อ local agent ไม่รัน: ระบบทำงานเหมือนเดิมทุกประการ — fallback ไป server workspace โดยอัตโนมัติ
- ผู้ใช้เห็นสถานะชัดเจนว่า local agent online/offline ใน UI

---

#### Task T2.1: Local agent detection — health check loop

**Type:** Feature
**Assigned To:** frontend-developer
**Estimated Time:** 2h
**Depends On:** T1.3

**Description**

เพิ่ม JavaScript module ใน `index.html` สำหรับตรวจสอบสถานะ local agent ด้วยการ poll `GET http://localhost:7000/health` ทุก 5 วินาที เก็บ state ใน module-level variable `localAgentState = { online: false, sandboxDir: null, port: 7000 }`

ใช้ `fetch()` พร้อม `signal: AbortController` timeout 2 วินาที เพื่อไม่ให้ health check block UI เมื่อ agent ไม่รัน ไม่ใช้ EventSource เพราะ health check ไม่ต้องการ streaming

**Evidence จาก codebase:** `index.html` line 2176 มี `fetch('/api/health')` ที่ poll health แล้ว — ใช้ pattern เดียวกัน แต่ target `http://localhost:7000/health` แทน relative path

```javascript
// Pattern ที่ต้องใช้ (based on existing health check pattern)
async function _checkLocalAgent() {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 2000);
  try {
    const res = await fetch(`http://localhost:${LOCAL_AGENT_PORT}/health`, { signal: ctrl.signal });
    const data = await res.json();
    localAgentState.online = data.status === 'ok';
    localAgentState.sandboxDir = data.sandbox || null;
  } catch {
    localAgentState.online = false;
    localAgentState.sandboxDir = null;
  } finally {
    clearTimeout(timer);
  }
}
```

**Acceptance Checklist**
- [ ] เมื่อ local agent รัน: `localAgentState.online === true` ภายใน 6 วินาที
- [ ] เมื่อ local agent หยุด: `localAgentState.online === false` ภายใน 7 วินาที
- [ ] Health check ไม่ทำให้ console error เมื่อ local agent ไม่รัน (ใช้ try/catch)
- [ ] AbortController timeout 2 วินาทีทำงานจริง (ไม่ block UI นาน)
- [ ] Port อ่านได้จาก constant `LOCAL_AGENT_PORT = 7000` ที่ define ครั้งเดียวในไฟล์
- [ ] Poll interval หยุดเมื่อ `document.hidden` เพื่อ conserve resource (Page Visibility API)

**Definition of Done**
```
DONE when:
  - Start/stop local_agent.py แล้ว state เปลี่ยนตาม ภายในรอบ poll ถัดไป
  - Console ไม่แสดง network error เมื่อ local agent ออฟไลน์
  - Reviewed โดย ui-ux-reviewer

NOT DONE if:
  - Health check throw uncaught promise rejection เมื่อ localhost refused
  - Poll ยังทำงานอยู่เมื่อ tab ถูก hide
```

**Fallback Plan**
```
If browser block cross-origin fetch ไป localhost:7000 เนื่องจาก mixed content หรือ CSP:
  Fallback: ใช้ image probe แทน fetch — สร้าง <img> ที่ src=http://localhost:7000/favicon.ico
             แล้วตรวจ onload/onerror เพื่อ detect online/offline
  Trade-off: ไม่ได้รับ sandbox path จาก response (แสดง UI generic แทน)
  Trigger: fetch ไป localhost:7000 ถูก block ใน Chrome console ด้วย CORS error แม้ header ถูกต้อง
  Decision Owner: frontend-developer + ต้องทดสอบบน Chrome Windows จริงก่อน T2.2
```

**Scaling Consideration**
```
Current: 1 poll ทุก 5 วินาที — < 1 KB network per check
Bottleneck at: N/A — single browser tab
Future-safe: Yes
```

---

#### Task T2.2: Intercept file save operations — route ไป local agent

**Type:** Feature
**Assigned To:** frontend-developer
**Estimated Time:** 3h
**Depends On:** T2.1

**Description**

แก้ logic การ save ใน `index.html` เมื่อ user กด "บันทึก" และ `localAgentState.online === true` ให้ intercept ก่อนที่จะส่ง save intent ไปยัง `/api/chat` บน server แทนที่จะให้ server เขียนไฟล์ลง server workspace ให้ browser เรียก `POST http://localhost:7000/files/create` โดยตรงและส่ง filename + content ที่ได้จาก `pendingDoc` หรือ `pendingTempPaths`

**สำคัญ:** สำหรับ PM mode ที่มี `pendingTempPaths` — content อยู่ที่ server ใน `temp/` ต้องเพิ่ม endpoint ใน `app.py` ที่ชื่อ `GET /api/temp/<filename>` เพื่อให้ browser ดึง content มาก่อนแล้วส่งต่อไปยัง local agent (browser เป็น relay) — ไม่ให้ local agent ยิง request ไปหา Flask server โดยตรง

**Evidence จาก codebase:**
- `index.html` line 1693 — `fetch('/api/chat', {...})` เป็น entry point หลัก
- `index.html` line 1770 — `data.type === 'pending_file'` เก็บ temp_path ที่ server
- `app.py` lines 251–271 — `handle_save()` เป็น server-side save ที่ต้อง bypass เมื่อ local agent online
- `app.py` line 295 — `handle_pm_save()` เป็น PM version ที่ต้อง bypass เช่นกัน

Flow เมื่อ local agent online + user กด "บันทึก":
```
1. browser ตรวจ localAgentState.online === true
2. [single doc mode] ใช้ pendingDoc content โดยตรง (อยู่ใน memory แล้ว)
   [PM mode] browser fetch GET /api/temp/<filename> สำหรับแต่ละ temp file
3. browser POST http://localhost:7000/files/create ด้วย filename + content
4. แสดง success/error feedback ใน UI
5. ส่ง cleanup request ไป /api/temp/<filename> (DELETE) เพื่อลบ temp file บน server
```

**Acceptance Checklist**
- [ ] เมื่อ local agent online + กด "บันทึก": ไฟล์ปรากฏใน sandbox dir บนเครื่อง user จริง
- [ ] เมื่อ local agent offline + กด "บันทึก": fallback ไป server save เหมือนเดิม ไม่มี error ที่ user เห็น
- [ ] PM mode (หลายไฟล์): ทุกไฟล์บันทึกครบ ไม่ข้ามไฟล์ไหน
- [ ] Duplicate filename: แสดง error `ไฟล์ชื่อนี้มีอยู่แล้วในโฟลเดอร์` พร้อม option rename
- [ ] ถ้า local agent ตอบ `{"ok":false}`: แสดง error message ที่ได้รับและ offer fallback ไป server
- [ ] Server workspace ยังคงสมบูรณ์ — ไม่มีไฟล์ซ้ำซ้อนบน server เมื่อ save local สำเร็จ

**Definition of Done**
```
DONE when:
  - ทดสอบ: start local_agent.py → สร้างเอกสารผ่าน AI → กด "บันทึก" → ไฟล์อยู่ใน C:\Users\...\sandbox จริง
  - ทดสอบ: หยุด local_agent.py → กด "บันทึก" → ไฟล์อยู่ใน server workspace เหมือนเดิม
  - ทดสอบ PM mode ทั้ง 2 scenario ข้างต้น
  - Reviewed โดย ui-ux-reviewer

NOT DONE if:
  - บันทึก local สำเร็จแต่ยังส่ง save request ไป server ด้วย (double-save)
  - Error จาก local agent ไม่แสดงใน UI (silent failure)
```

**Fallback Plan**
```
If /api/temp/<filename> endpoint ยาก implement หรือ security review ไม่ผ่าน:
  Fallback: สำหรับ PM mode ในระยะแรก ให้ fallback ไป server save เสมอ (local agent สำหรับ single doc เท่านั้น)
  Trade-off: PM mode ไม่รองรับ local agent จนกว่าจะ implement temp endpoint
  Trigger: temp endpoint implementation เกิน 4h หรือ security checker raise concern
  Decision Owner: backend-developer ต้อง sign off ก่อน implement temp endpoint
```

**Scaling Consideration**
```
Current: content ส่งผ่าน browser memory — ไม่มี file size limit จาก HTTP (ยกเว้น browser memory)
Bottleneck at: เอกสารขนาด > 10MB อาจช้าเนื่องจาก base64 encode/decode
Mitigation: เพิ่ม client-side size check ก่อน send — แสดง warning ถ้า content > 5MB
Future-safe: Yes สำหรับ use case ปกติ (เอกสาร text)
```

**Maintainability Note**
สร้าง function `saveToLocalAgent(filename, content)` ที่ return Promise เพื่อให้ single doc และ PM mode ใช้ร่วมกัน ไม่ duplicate fetch logic

---

#### Task T2.3: Error handling + fallback UX สำหรับ local save

**Type:** Feature
**Assigned To:** frontend-developer
**Estimated Time:** 2h
**Depends On:** T2.2

**Description**

Handle error cases ทุกรูปแบบที่อาจเกิดขึ้นระหว่าง local save และนำเสนอ user ด้วย UX ที่ชัดเจน:

1. **Local agent timeout** (ไม่ตอบใน 10 วินาที): แสดง "Local agent ไม่ตอบสนอง กำลัง fallback ไปยัง server..."
2. **File exists on local** (409): แสดง inline prompt "ไฟล์ชื่อนี้มีอยู่แล้ว — เขียนทับ / เปลี่ยนชื่อ / ยกเลิก"
3. **Path traversal rejected** (400): แสดง "ชื่อไฟล์ไม่ปลอดภัย กรุณาแก้ไขชื่อไฟล์"
4. **Network error** (fetch throws): auto-fallback ไป server save เงียบ ๆ + tooltip แจ้ง
5. **Local agent went offline** ระหว่าง save: retry 1 ครั้ง ถ้ายัง fail ให้ fallback

**Evidence จาก codebase:** `index.html` line ประมาณ 1838 — `data.type === 'save_failed'` มี pattern `restorePendingState()` แล้ว ให้ใช้ pattern เดียวกันกับ local save failure

**Acceptance Checklist**
- [ ] Error case ทั้ง 5 ข้างต้น มี UI feedback ที่ user เห็น (ไม่ silent fail)
- [ ] Auto-fallback ทำงานโดยไม่ต้องให้ user กด confirm ในกรณี network error
- [ ] File exists dialog มี 3 ตัวเลือก: เขียนทับ, เปลี่ยนชื่อ (append timestamp), ยกเลิก
- [ ] Pending state ยังอยู่ครบหลัง error ทุกกรณี (user ไม่สูญเสียงาน)
- [ ] ไม่มี unhandled promise rejection ใน console

**Definition of Done**
```
DONE when:
  - ทดสอบ error ทั้ง 5 case โดยจำลอง: kill agent กลางคัน, สร้างไฟล์ชื่อซ้ำ, ส่ง filename มี ../
  - ทุก case มี feedback ที่ user เห็น
  - Pending content ไม่สูญหายในทุก error case

NOT DONE if:
  - Error ทำให้ chat เงียบ และ input box disable ค้าง
  - User ต้อง refresh หน้าเพื่อกู้คืน state หลัง local save fail
```

**Fallback Plan**
```
If inline dialog สำหรับ file conflict ซับซ้อนเกินไปใน timeline:
  Fallback: auto-rename โดย append timestamp suffix เสมอ (ไม่ถามผู้ใช้)
  Trade-off: user ได้ไฟล์ชื่อใหม่โดยไม่รู้ตัว แต่ไม่สูญเสียงาน
  Trigger: inline dialog implementation เกิน 2h
  Decision Owner: frontend-developer
```

---

#### Task T2.4: Review + ทดสอบ integration บน Windows

**Type:** Testing
**Assigned To:** ui-ux-reviewer
**Estimated Time:** 1h
**Depends On:** T2.3

**Description**

รัน `ui-ux-reviewer` subagent ตาม mandatory review order ทดสอบ integration ทั้งหมดบน Windows 11 Chrome จริง ครอบคลุม happy path และ error paths

**Acceptance Checklist**
- [ ] ui-ux-reviewer ผ่านโดยไม่มี UX issue ระดับ HIGH
- [ ] ทดสอบบน Chrome Windows จริง (ไม่ใช่แค่ WSL browser)
- [ ] CHANGELOG.md อัปเดตเป็น v0.23.0

---

### Phase 3 — UI: Directory Picker + Status Indicator | 5h | User เลือก sandbox directory ผ่าน UI และเห็นสถานะ local agent ชัดเจน

**Phase Exit Criteria:**
- มี indicator ใน sidebar แสดง local agent online/offline พร้อม sandbox path
- User เปลี่ยน sandbox directory ได้ผ่าน UI โดยไม่ต้องแก้ code
- instruction ของ `local_agent.py` startup แสดงใน UI ได้

---

#### Task T3.1: Local agent status indicator ใน sidebar

**Type:** Feature
**Assigned To:** frontend-developer
**Estimated Time:** 3h
**Depends On:** T2.3

**Description**

เพิ่ม status widget ใน sidebar footer ของ `index.html` (บริเวณเดียวกับ theme-btn) แสดงสถานะ local agent:

- **Online:** dot สีเขียว + "Local Agent: เชื่อมต่อแล้ว" + truncated sandbox path
- **Offline:** dot สีเทา + "Local Agent: ไม่ได้เชื่อมต่อ" + ลิงก์ help text "วิธีเปิดใช้งาน?"

เมื่อ click "วิธีเปิดใช้งาน?" ให้แสดง modal ที่มีคำแนะนำ startup command เช่น:
```
python local_agent.py --sandbox-dir "C:\Users\username\Documents\AI-Files"
```

เมื่อ online ให้ widget มี dropdown เล็ก ๆ ที่ show sandbox path และมี "เปลี่ยน folder" ซึ่ง trigger prompt ให้ local agent restart ด้วย path ใหม่ (ไม่ implement hot-switch — แค่แสดง restart command)

**Evidence จาก codebase:** `index.html` lines 223–248 — `.theme-btn` pattern ใน sidebar footer เป็น template ที่ดี สำหรับ icon + text layout

**Acceptance Checklist**
- [ ] Widget อัปเดต state ภายใน 6 วินาทีเมื่อ agent start/stop
- [ ] Offline state ไม่แสดง sandbox path (เพราะยังไม่รู้)
- [ ] Online state แสดง path ที่ truncate ด้วย CSS `text-overflow: ellipsis` ไม่ล้น sidebar
- [ ] Help modal แสดง command ที่ copy-paste ได้ทันที (monospace font, one-click copy)
- [ ] Widget ทำงานถูกต้องทั้ง light mode และ dark mode
- [ ] ใช้ CSS variables ที่มีอยู่แล้ว ไม่เพิ่ม color hardcode ใหม่

**Definition of Done**
```
DONE when:
  - Widget แสดงสถานะถูกต้องทั้ง online/offline
  - Help modal มี command ที่รันได้จริงบน Windows
  - Reviewed โดย ui-ux-reviewer

NOT DONE if:
  - Widget ใช้ inline style แทน CSS variables
  - Help command ไม่ถูกต้องบน Windows (ใช้ / แทน \)
```

**Fallback Plan**
```
If sidebar footer overflow เมื่อเพิ่ม widget:
  Fallback: ย้าย indicator ไปอยู่ใน workspace selector bar แทน (ใกล้ workspacePath element)
  Trade-off: visibility ลดลงเล็กน้อย แต่ไม่กระทบ layout
  Trigger: sidebar มี scrollbar เพิ่มขึ้นหลังเพิ่ม widget
  Decision Owner: frontend-developer
```

---

#### Task T3.2: Directory picker — เปลี่ยน sandbox path ผ่าน UI

**Type:** Feature
**Assigned To:** frontend-developer
**Estimated Time:** 2h
**Depends On:** T3.1

**Description**

เพิ่ม endpoint `POST http://localhost:7000/config/sandbox` ใน `local_agent.py` ที่รับ `{"sandbox_dir":"<path>"}` แล้ว validate และ update sandbox path ใน runtime (ไม่ต้อง restart) พร้อม return `{"ok":true,"sandbox":"<new_path>"}` หรือ error

ฝั่ง UI เพิ่ม input field ใน local agent modal ที่ใช้งานง่าย: text input + "เปลี่ยน" button ส่ง POST ไป `/config/sandbox` แล้วอัปเดต widget

**หมายเหตุ security:** path ที่รับจาก UI ต้องผ่าน `os.path.exists()` + `os.path.isdir()` และ resolv absolute ก่อน accept ห้าม accept relative path หรือ path ที่ไม่ exist

**Acceptance Checklist**
- [ ] เปลี่ยน sandbox dir ผ่าน UI แล้วไฟล์ถัดไปบันทึกใน dir ใหม่จริง
- [ ] Path ที่ไม่ exist ถูก reject พร้อม error message ใน UI
- [ ] Relative path (เช่น `../Desktop`) ถูก reject
- [ ] Windows path ที่มี backslash ทำงานได้ (Python `Path()` handle ได้แล้ว)
- [ ] หลังเปลี่ยน path แล้ว health check ตอบ sandbox ใหม่

**Definition of Done**
```
DONE when:
  - เปลี่ยน sandbox path ผ่าน UI ได้โดยไม่ restart local_agent.py
  - Invalid path ถูก reject ก่อนบันทึก
  - v0.24.0 commit สร้างแล้ว

NOT DONE if:
  - เปลี่ยน path แล้ว old path ยังใช้งานได้ (race condition)
  - ไม่มี mutex ป้องกัน concurrent config change กับ file operation
```

**Fallback Plan**
```
If hot-switch sandbox path ยากเนื่องจาก threading:
  Fallback: ไม่รองรับ hot-switch — แค่แสดง restart command ในรูปแบบที่ copy-ปิดได้
  Trade-off: user ต้อง restart local_agent.py ด้วยตัวเอง
  Trigger: hot-switch implementation ต้องใช้ thread lock > 30 บรรทัด
  Decision Owner: backend-developer
```

---

### Phase 4 — Optional: local_agent_tray.py | 5h | Tray icon wrapper สำหรับ Windows user ที่ไม่ต้องการรัน CLI

**Phase Exit Criteria:** (Optional Phase — ทำหรือไม่ทำได้โดยไม่กระทบ Phase 1-3)
- Double-click `local_agent_tray.py` แล้ว icon ปรากฏใน system tray
- Right-click tray icon มี menu: เปิด folder, เปลี่ยน folder, หยุดทำงาน
- ปิดหน้าต่างได้โดยไม่หยุด background server

---

#### Task T4.1: Tray icon wrapper ด้วย pystray

**Type:** Feature
**Assigned To:** backend-developer
**Estimated Time:** 3h
**Depends On:** T1.3

**Description**

สร้าง `local_agent_tray.py` ที่ import `local_agent.py` แล้ว run HTTP server ใน background thread พร้อม `pystray` tray icon บน Windows Tray menu ต้องมี:
- "Local Agent — กำลังทำงาน" (disabled label แสดงสถานะ)
- "เปิดโฟลเดอร์ Sandbox" — เปิด Explorer ไปที่ sandbox dir
- "หยุดทำงาน" — stop server thread แล้ว exit

ต้องสร้างไฟล์ `requirements_tray.txt` แยกต่างหาก (ไม่ merge เข้า `requirements.txt` หลัก) เพื่อไม่ให้ server environment ต้องติดตั้ง pystray

**Acceptance Checklist**
- [ ] `pip install pystray pillow` แล้วรันได้บน Windows 11
- [ ] Tray icon ปรากฏใน system tray
- [ ] "เปิดโฟลเดอร์ Sandbox" เปิด Windows Explorer ที่ถูกต้อง
- [ ] "หยุดทำงาน" หยุด HTTP server สะอาด (ไม่มี port ค้าง)
- [ ] `local_agent.py` ยังรันได้แบบ standalone CLI โดยไม่ต้องมี pystray

**Definition of Done**
```
DONE when:
  - ทดสอบบน Windows 11 จริง
  - local_agent.py ยัง import-free จาก pystray
  - requirements_tray.txt สร้างแล้ว

NOT DONE if:
  - local_agent.py ต้อง import pystray (ทำลาย standalone mode)
  - Tray icon crash เมื่อ DPI scaling > 100%
```

**Fallback Plan**
```
If pystray ไม่ compatible กับ Windows 11 หรือ DPI scaling มีปัญหา:
  Fallback: สร้าง local_agent_start.bat และ local_agent_stop.bat แทน
  Trade-off: ไม่มี tray icon แต่ user คลิก batch file ได้ง่าย
  Trigger: pystray crash บน Windows 11 หลังลอง 2 วิธีแล้ว
  Decision Owner: backend-developer
```

---

#### Task T4.2: บรรจุเป็น Windows executable (Optional)

**Type:** Infrastructure
**Assigned To:** backend-developer
**Estimated Time:** 2h
**Depends On:** T4.1

**Description**

ใช้ `pyinstaller` บรรจุ `local_agent_tray.py` เป็น `.exe` เพื่อให้ user ที่ไม่มี Python ใช้ได้ สร้าง `build_local_agent.bat` script ที่รัน pyinstaller ด้วย flag ที่ถูกต้อง (`--onefile --windowed --name LocalAgent`)

**Acceptance Checklist**
- [ ] `LocalAgent.exe` รันได้บนเครื่องที่ไม่มี Python ติดตั้ง
- [ ] Windows Defender SmartScreen ไม่ block (หรือมี instruction ให้ user click "Run anyway")
- [ ] Exe size < 30MB
- [ ] `build_local_agent.bat` รันได้ใน 1 คำสั่ง

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|-----------|--------|------------|-------|
| R1 | Browser block CORS fetch ไป localhost:7000 เนื่องจาก Chrome security policy เปลี่ยน | Medium | High | ทดสอบ CORS บน Chrome Windows จริงก่อน implement T2.2 ใช้ image probe เป็น fallback | frontend-developer |
| R2 | Windows path separator `\` ทำให้ `_validate_path()` fail เนื่องจาก `commonpath()` behavior ต่างกัน | Medium | High | เพิ่ม unit test เฉพาะ Windows path ใน T1.2 ทดสอบบน Windows จริง ไม่ใช่แค่ WSL | backend-developer |
| R3 | User เปิด local agent บน WSL แต่ browser บน Windows — localhost:7000 ไม่ตรงกัน | High | High | README ต้องระบุชัดว่า local_agent.py ต้องรันบน Windows โดยตรง (ไม่ใช่ WSL) เพิ่ม warning ใน startup | backend-developer |
| R4 | Content ขนาดใหญ่ (เอกสาร PM หลายชิ้น) ทำให้ browser memory เต็มระหว่าง relay | Low | Medium | เพิ่ม client-side size check 5MB per file ก่อน fetch temp content | frontend-developer |
| R5 | local_agent.py ถูก AV/Windows Defender flag เนื่องจาก HTTP server + file write | Medium | Medium | ไม่ใช้ pyinstaller ในทีแรก ใช้ CLI mode ก่อน ถ้า AV block ให้ document whitelist procedure | backend-developer |
| R6 | User ลืม start local_agent.py ก่อนใช้งาน ทำให้ save ไป server โดยไม่รู้ตัว | High | Low | Status indicator ใน UI ชัดเจน (Phase 3) และ tooltip reminder เมื่อ save สำเร็จ | frontend-developer |
| R7 | temp file cleanup บน server ไม่เกิดขึ้นเมื่อ browser relay ล้มเหลวกลางคัน | Medium | Low | เพิ่ม cleanup endpoint ที่ browser เรียกหลัง save ทุกกรณี (success + error) | backend-developer |

**Risk Classification:**
- R1, R2, R3 — ต้อง resolve ก่อนเริ่ม Phase 2 (ทดสอบ CORS บน Windows จริงก่อน)
- R4, R5, R6, R7 — plan mitigation ก่อน Phase 2 เสร็จ

---

## Fallback Strategy Map

```
Primary Plan
    └── Phase 1 fail (CORS บน stdlib http.server ไม่ work บน Chrome)
          → ใช้ Flask minimal app แทน stdlib (ใช้ venv ที่มีอยู่แล้ว)
    └── Phase 2 T2.1 fail (browser block localhost fetch)
          → ใช้ image probe สำหรับ detection + WebSocket แทน REST สำหรับ operations
    └── Phase 2 T2.2 fail (PM mode temp relay ซับซ้อนเกิน)
          → Phase 1: local agent รองรับเฉพาะ single-doc mode ก่อน
          → PM mode local save เพิ่มใน v0.26.0
    └── Phase 3 fail (sidebar overflow หรือ UI review ไม่ผ่าน)
          → ย้าย status indicator ไปอยู่ใน workspace selector area
    └── Phase 4 fail (pystray DPI crash บน Windows 11)
          → สร้าง .bat wrapper แทน tray icon

Timeline slip mitigation:
    Must-have (non-negotiable): Phase 1 + Phase 2 T2.1 + T2.2 + T2.3
    Nice-to-have (deferrable): Phase 3 T3.2 (directory picker), Phase 4 ทั้งหมด
    Absolute minimum MVP: local_agent.py รันได้ + browser fallback ทำงาน (ไม่ต้องมี UI indicator)
```

---

## Scale & Maintainability Matrix

| Component | Current Capacity | Bottleneck Threshold | Scale Strategy | Maintainability |
|-----------|-----------------|---------------------|----------------|-----------------|
| local_agent.py HTTP server | 1 concurrent request (stdlib) | ~5 concurrent (PM mode ส่งหลาย request พร้อมกัน) | ThreadingTCPServer ใน T1.3 | High — handler แยก method |
| Browser health check poll | 1 fetch ทุก 5s | N/A — single user | Page Visibility API หยุด poll เมื่อ tab hidden | High — isolated function |
| Browser relay (temp files) | Content ใน memory | ~5MB per file ก่อน OOM | Client-side size check + streaming ถ้าจำเป็น | Medium — ต้องระวัง memory leak |
| _validate_path() | Instant | N/A — pure computation | ไม่จำเป็น | High — ported จาก mcp_server.py |

**Scaling Principles Applied:**
- [x] Stateless local agent — ทุก request self-contained
- [x] ไม่มี hardcoded capacity limits — port และ sandbox path อ่านจาก config
- [ ] Database read/write separation — N/A
- [x] Async timeout บน browser health check (AbortController)
- [ ] Cache invalidation — N/A สำหรับ local files
- [x] Page Visibility API ลด poll overhead

**Maintainability Principles Applied:**
- [x] Single responsibility — local_agent.py ทำแค่ HTTP server ไม่มี business logic อื่น
- [x] Configuration externalized — port, sandbox, CORS origins เป็น env vars / CLI args
- [x] _validate_path() interface เหมือน mcp_server.py — test เดียวกันใช้ได้
- [x] localAgentState เป็น module-level object เดียว ไม่กระจายสถานะ
- [x] saveToLocalAgent() เป็น function เดียว ใช้ทั้ง single-doc และ PM mode

---

## Timeline View

```
Week 1                      Week 2
┌──────────────────────────┬──────────────────────────┐
│ Phase 1 (1-2 วัน)        │ Phase 2 (2-3 วัน)        │
│ T1.1 HTTP server + CORS  │ T2.1 health check loop   │
│ T1.2 path sandbox        │ T2.2 intercept file save │
│ T1.3 file endpoints      │ T2.3 error handling      │
│ T1.4 review + test       │ T2.4 Windows integration │
│ Phase Exit: v0.22.0      │ Phase Exit: v0.23.0      │
└──────────────────────────┴──────────────────────────┘
         ↓                            ↓
   [Milestone 1]               [Milestone 2]
   local_agent.py             Browser proxy
   standalone ready           working on Windows

Week 3 (ถ้ามีเวลา)
┌──────────────────────────┐
│ Phase 3 (1-2 วัน)        │
│ T3.1 status indicator    │
│ T3.2 directory picker    │
│ Phase Exit: v0.24.0      │
│ Phase 4 (Optional)       │
│ T4.1 pystray tray        │
│ T4.2 exe packaging       │
│ v0.25.0                  │
└──────────────────────────┘
         ↓
   [LAUNCH v0.24.0 MVP]
```

---

## Testing Strategy

### Unit Testing

**Scope:** `_validate_path()` บน local_agent.py ทุก edge case

**Tool:** pytest (มีอยู่แล้วใน venv ผ่าน test_cases.py)

**Coverage Target:** 100% บน `_validate_path()` (security-critical), 80% บน endpoint handlers

**Key Test Cases:**
```
test_path_traversal_unix      → ../etc/passwd → ValueError
test_path_traversal_windows   → ..\Windows\System32\ → ValueError
test_path_symlink_escape       → symlink ชี้ออกนอก sandbox → ValueError
test_path_null_byte            → filename\x00.txt → ValueError / reject
test_path_valid_nested         → subdir/file.txt ที่อยู่ใน sandbox → pass
test_path_windows_absolute     → C:\sandbox\file.txt → pass เมื่อ sandbox = C:\sandbox
test_content_thai_roundtrip    → เขียน Thai content แล้วอ่านกลับได้ครบ
```

### Integration Testing

**Scope:** Browser ↔ local_agent.py ↔ filesystem

**Key Scenarios:**
- [ ] Single doc save: AI สร้างเอกสาร → user กด "บันทึก" → ไฟล์ปรากฏใน sandbox dir
- [ ] PM mode save: 3 subtask docs → บันทึกครบ 3 ไฟล์
- [ ] Fallback: หยุด local_agent.py ระหว่าง session → save ต่อไปบน server ได้
- [ ] Path traversal via UI: ส่ง filename มี `../` จาก UI → local agent reject 400
- [ ] Agent restart: restart local_agent.py กลางคัน → browser detect ภายใน 10s → save ทำงานต่อ

### Manual Smoke Test (ก่อน commit v0.23.0)

- [ ] เปิด `python local_agent.py --sandbox-dir C:\Users\test\sandbox` บน Windows CMD
- [ ] เปิด browser ไปที่ `http://localhost:5000` เห็น local agent status เป็น online
- [ ] พิมพ์: "สร้างสัญญาจ้างงานสำหรับนายสมชาย"
- [ ] AI สร้างเอกสาร → กด "บันทึก" → เห็น success message
- [ ] เปิด `C:\Users\test\sandbox` ใน File Explorer → เห็นไฟล์ .md
- [ ] หยุด local_agent.py → กด "บันทึก" อีกครั้ง → ไฟล์บันทึกใน server workspace แทน
- [ ] ไม่มี error ใน browser console

---

## Definition of Done — Project Level

```
DONE when:
  - Phase 1 + Phase 2 Exit Criteria ครบ (Phase 3, 4 optional)
  - Unit test ผ่านทุก path traversal case
  - ทดสอบ manual smoke test ครบ 7 ขั้นตอนข้างต้น
  - ไม่มี silent failure — ทุก error มี UI feedback
  - backend-python-reviewer และ ui-ux-reviewer ผ่านทั้งสอง phase
  - README หรือ comment ใน local_agent.py อธิบาย startup command บน Windows
  - v0.23.0 commit มี CHANGELOG entry ครบถ้วน

NOT DONE if:
  - ทดสอบเฉพาะใน WSL แต่ไม่ได้รันบน Windows CMD จริง
  - local agent online แต่ fallback ไม่ทำงานเมื่อ agent offline
  - Path traversal bypass ได้ผ่าน filename ที่ encode พิเศษ
  - ไม่มี status indicator ใน UI (user ไม่รู้ว่า save ไปที่ไหน)
  - Server workspace มี duplicate files จากการ double-save
```

---

## Assumptions & Open Questions

**Assumptions Made:**

1. User รัน browser บน Windows และรัน local_agent.py บน Windows เดียวกัน (ไม่ใช่ WSL) — ถ้าผิด: localhost:7000 จาก WSL ไม่ resolve ถึงได้จาก Windows browser ต้องใช้ WSL IP แทน
2. Chrome version ใหม่พอที่จะ allow fetch ไป localhost cross-origin ด้วย CORS header ที่ถูกต้อง — ถ้าผิด: ต้องใช้ image probe fallback จาก T2.1
3. project ใช้ venv ที่มี Flask อยู่แล้ว — ถ้าผิด: local_agent.py ต้องใช้ stdlib เท่านั้น และ CORS handling ยากขึ้น
4. เนื้อหาเอกสารที่ AI สร้างมีขนาด < 5MB ต่อชิ้น — ถ้าผิด: ต้องเพิ่ม streaming/chunked transfer ใน browser relay

**Open Questions (ต้อง resolve ก่อนเริ่ม Phase ที่ระบุ):**

- Q1: Chrome บน Windows ปี 2026 อนุญาต fetch cross-origin ไป http://localhost:7000 จาก http://localhost:5000 ด้วย CORS header เท่านั้นหรือไม่? หรือต้องการ `--disable-web-security` flag เพิ่ม? — **ต้องทดสอบก่อน Phase 2 | Owner: frontend-developer**
- Q2: `/api/temp/<filename>` endpoint ที่ expose temp file content มี security concern ไหม? (temp file มีเนื้อหา AI draft ที่ user ยังไม่ confirm) — **ต้องตอบก่อน T2.2 | Owner: backend-developer + security-checker**
- Q3: Windows Defender หรือ AV อื่นบนเครื่อง user จะ block local_agent.py ที่เปิด HTTP server ไหม? มีวิธี whitelist ที่แนะนำได้ไหม? — **ต้องทดสอบก่อน Phase 1 complete | Owner: backend-developer**

---

## Handoff Notes

**backend-developer (สร้าง local_agent.py):**
- `_validate_path()` ต้อง copy จาก `mcp_server.py` lines 14–25 โดยตรง อย่า rewrite — logic เหมือนกัน 100% เพื่อให้ test เดียวกันใช้ได้
- ใช้ `socketserver.ThreadingTCPServer` ไม่ใช่ `TCPServer` เพื่อรองรับ concurrent request จาก PM mode (browser ส่งหลาย request พร้อมกันได้)
- Response JSON ต้องมี `"ok": true/false` เสมอ ไม่ใช้ emoji string เพราะ frontend ต้อง parse programmatically
- Test บน Windows CMD จริง ไม่ใช่แค่ WSL — path separator และ socket behavior ต่างกัน
- ถ้าใช้ Flask (fallback): ใช้ `./venv/bin/python local_agent.py` ไม่ต้อง pip install ใหม่

**frontend-developer (แก้ index.html):**
- `localAgentState` เป็น module-level object เดียว อย่า spread สถานะไปหลายตัวแปร
- health check function ต้อง swallow network error (try/catch) เพราะ `connection refused` เป็น expected state ไม่ใช่ bug
- ใช้ pattern `AbortController` เหมือน health check ที่มีอยู่แล้วใน `index.html` line 2176
- `saveToLocalAgent(filename, content)` ต้อง return `{ok, error}` object ไม่ throw เพื่อให้ caller จัดการ fallback ได้
- CSS ใช้ CSS variables ที่มีอยู่แล้ว (`--hr-fg`, `--outline`, etc.) อย่าเพิ่ม color ใหม่

**backend-python-reviewer:**
- Review focus หลัก: CORS header ถูกต้องและ restrict ถึงแค่ allowlist, path traversal ทุก case, bare except
- ต้องทดสอบ path กับ Windows path separator ด้วย (ไม่ใช่แค่ Unix)
- ตรวจ R3: README ต้องระบุว่า local_agent.py รันบน Windows ไม่ใช่ WSL

**devops / การ deploy:**
- ไม่ต้องแก้ server config ใดๆ สำหรับ feature นี้ — ทุกอย่างรันบนเครื่อง user
- `local_agent.py` ไม่ใช่ส่วนของ Flask server deployment
- Environment variables ใหม่สำหรับ local_agent.py: `LOCAL_AGENT_PORT` (default 7000), `LOCAL_AGENT_SANDBOX` (required ถ้าไม่ผ่าน CLI args)
