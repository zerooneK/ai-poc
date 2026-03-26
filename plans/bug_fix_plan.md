# Bug Fix Plan — v0.15.0
## วันที่: 26 มีนาคม 2569

---

## สรุป Bugs ที่พบ (พร้อมหลักฐาน)

| # | Severity | Bug | File:Line | Confirmed |
|---|----------|-----|-----------|-----------|
| C1 | CRITICAL | `_SAVE_KEYWORDS` substring false positive (`'ok'`) | `app.py:190,198` | YES |
| C2 | CRITICAL | PM task output ไม่ถูก push ใน `conversationHistory` | `index.html:1840,1889-1891` | YES |
| H1 | HIGH | `_web_search` ไม่มี timeout | `core/utils.py:27` | YES |
| H2 | HIGH | `stream_response` ไม่มี exception handling | `agents/base_agent.py:39-47` | YES |
| H3 | HIGH | Partial document เข้า pending confirmation หลัง error | `index.html:1881-1888` | YES |
| H4 | HIGH | `global WORKSPACE_PATH` ใน `set_workspace_api` แก้ local binding | `app.py:471,476` | YES |
| H5 | HIGH | `GeneratorExit` ไม่ถูก handle ใน `stream_response` / `run_with_tools` | `agents/base_agent.py:39-47,64-71` | YES |
| H6 | HIGH | `copyOutput()` copy แค่ subtask สุดท้ายใน PM task | `index.html:1945-1946` | YES |
| M1 | MEDIUM | N+1 Queries ใน `db.get_history` | `db.py:226-233` | YES |
| M2 | MEDIUM | `OPENROUTER_API_KEY` ไม่มี startup validation | `core/shared.py:9,41-45` | YES |
| M3 | MEDIUM | `reader.cancel()` ขาดใน catch block | `index.html:1923-1941` | YES |
| M4 | MEDIUM | `handle_pm_save` ดึง agent type จากชื่อไฟล์ fragile | `app.py:308` | YES |
| M5 | MEDIUM | ไม่มี size limit บน `pending_doc` | `app.py:341,350` | YES |
| L1 | LOW | `pmSubtaskIndex` dead variable | `index.html` — ไม่พบในโค้ด (already removed) | NOT FOUND |

---

## แผนการแก้ไขแต่ละ Bug

---

### C1 — `_SAVE_KEYWORDS` substring false positive (`'ok'`)

**หลักฐาน:** `app.py:190,198`

**Code ที่มีปัญหา:**
```python
# app.py:190
_SAVE_KEYWORDS = {'บันทึก', 'save', 'เซฟ', 'ยืนยัน', 'ตกลง', 'ได้เลย', 'ok', 'โอเค', 'บันทึกได้', 'บันทึกเลย', 'บันทึกได้เลย', 'ใช้ได้'}

# app.py:195-198
def _is_save_intent(message: str) -> bool:
    msg = message.lower().strip()
    if any(neg in msg for neg in _SAVE_NEGATIVE_PREFIX): return False
    return any(kw in msg for kw in _SAVE_KEYWORDS)
```

**ปัญหา:**
`'ok' in msg` ใช้ substring matching ดังนั้น message เช่น `"สร้างสัญญาจ้างงานให้กับ มานะ โอกาสดี"` จะ match ตรง `"โอกาสดี"` เพราะ `'ok'` เป็น substring ของ `'โอกาส'` (เมื่อ lower) ได้ หรือ message อย่าง `"ดูข้อมูล stock"` ก็ match `'ok'` ใน `'stock'` ได้ทันที ส่งผลให้ message ที่ผู้ใช้ส่งมาเพื่อสร้างเอกสารใหม่กลายเป็น save intent ผิดพลาด

**วิธีแก้:**
แยก keyword ที่ต้องการ word-boundary check ออกจาก set และใช้ regex แทน:

```python
# app.py:190-198 — แก้ใหม่
import re as _re

_SAVE_KEYWORDS_EXACT = {'บันทึก', 'save', 'เซฟ', 'ยืนยัน', 'ตกลง', 'ได้เลย', 'โอเค', 'บันทึกได้', 'บันทึกเลย', 'บันทึกได้เลย', 'ใช้ได้'}
_SAVE_KEYWORDS_WORD_BOUNDARY = re.compile(r'\bok\b', re.IGNORECASE)
_SAVE_NEGATIVE_PREFIX = {'ไม่ใช่', 'ไม่ใช้'}
_DISCARD_KEYWORDS = {'ยกเลิก', 'cancel', 'ไม่เอา', 'ไม่บันทึก', 'ไม่ต้องการ', 'ข้ามไป', 'ลบทิ้ง', 'discard'}
_EDIT_KEYWORDS = {'แก้ไข', 'แก้', 'ปรับ', 'ปรับปรุง', 'ปรับแก้', 'เพิ่ม', 'ลบ', 'เปลี่ยน', 'แทนที่', 'เพิ่มเติม', 'ตัดออก', 'แก้ตรง', 'ปรับตรง', 'edit', 'modify', 'update', 'change', 'fix', 'adjust', 'add', 'remove', 'delete', 'replace', 'revise'}

def _is_save_intent(message: str) -> bool:
    msg = message.lower().strip()
    if any(neg in msg for neg in _SAVE_NEGATIVE_PREFIX): return False
    return any(kw in msg for kw in _SAVE_KEYWORDS_EXACT) or bool(_SAVE_KEYWORDS_WORD_BOUNDARY.search(msg))
```

นอกจากนี้ต้องแก้ `_isSaveIntentJS` ใน `index.html:1207` ให้ตรงกัน:

```javascript
// index.html:1207 — แก้ใหม่
function _isSaveIntentJS(msg) {
  return /บันทึก|save|ยืนยัน|confirm|ตกลง|\bok\b/i.test(msg);
}
```

**ผลกระทบ:** ป้องกัน false positive save intent บน message ที่มีคำว่า `ok` เป็น substring (เช่น `stock`, `โอกาส`, `outlook`) ไม่มีผลต่อ `ok` ที่ standalone
**ลำดับ:** 1 (แก้ก่อนสุด — high business impact)

---

### C2 — PM task output ไม่ถูก push ใน `conversationHistory`

**หลักฐาน:** `index.html:1831-1841` และ `index.html:1889-1891`

**Code ที่มีปัญหา:**
```javascript
// index.html:1831-1841 — subtask_done handler
} else if (data.type === 'subtask_done') {
    outputText = outputText
      .replace(/\{[^{}]*"(?:request|tool)"\s*:\s*"[^"]*"[^{}]*\}/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    if (outputText) {
      _renderMarkdown(currentOutputEl, outputText);
    }
    outputText = '';   // <-- reset ทิ้งทุก subtask
    // ...
}

// index.html:1889-1891 — done handler ตรวจ outputText
if (outputText) {
  conversationHistory.push({ role: 'assistant', content: outputText });
}
```

**ปัญหา:**
`subtask_done` reset `outputText = ''` ทุกครั้งหลัง render แต่ `done` handler push `outputText` เข้า `conversationHistory` หลังจาก loop จบ ดังนั้น `outputText` จะเป็น `''` เสมอสำหรับ PM task ทำให้ไม่มีอะไรเข้า history และ AI จะไม่จำ PM output ในการสนทนารอบต่อไป

**วิธีแก้:**
สะสม PM subtask output ไว้ใน accumulator variable และส่งเข้า history ตอน `done`:

```javascript
// index.html — เพิ่ม accumulator ข้าง state variables (ประมาณบรรทัด 1368)
let pmOutputAccumulator = [];   // สะสม subtask output ของ PM task

// index.html — subtask_done handler แก้ไข
} else if (data.type === 'subtask_done') {
    outputText = outputText
      .replace(/\{[^{}]*"(?:request|tool)"\s*:\s*"[^"]*"[^{}]*\}/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    if (outputText) {
      _renderMarkdown(currentOutputEl, outputText);
      pmOutputAccumulator.push(outputText);   // <-- สะสมไว้
    }
    outputText = '';
    // ... (ส่วนที่เหลือเหมือนเดิม)
}

// index.html — done handler แก้ไขส่วน conversationHistory push
// แก้จาก:
if (outputText) {
  conversationHistory.push({ role: 'assistant', content: outputText });
}
wasPMTask = false;

// แก้เป็น:
const historyContent = wasPMTask
  ? pmOutputAccumulator.join('\n\n---\n\n')
  : outputText;
if (historyContent) {
  conversationHistory.push({ role: 'assistant', content: historyContent });
}
pmOutputAccumulator = [];   // reset accumulator
wasPMTask = false;
```

**ผลกระทบ:** PM task จะถูกบันทึกใน conversation history อย่างถูกต้อง ทำให้ AI เข้าใจ context ของ PM output ในรอบการสนทนาถัดไป ไม่มีผลต่อ single-agent flow
**ลำดับ:** 2

---

### H1 — `_web_search` ไม่มี timeout

**หลักฐาน:** `core/utils.py:21-36`

**Code ที่มีปัญหา:**
```python
# core/utils.py:21-36
def _web_search(query: str, max_results: int = 5) -> str:
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):   # ไม่มี timeout
                results.append(...)
```

**ปัญหา:**
`DDGS().text()` ไม่มี timeout parameter ดังนั้นถ้า DuckDuckGo ตอบช้าหรือ network hang SSE stream จะ block อยู่ที่นี่ตลอดไป ซึ่งจะกิน thread ของ Flask และ user ไม่เห็น error message

**วิธีแก้:**
ใช้ `DDGS(timeout=X)` ตาม DDGS library API และ wrap ด้วย `concurrent.futures.ThreadPoolExecutor` เพื่อให้มี hard timeout:

```python
# core/utils.py:21-36 — แก้ใหม่
_WEB_SEARCH_TIMEOUT = float(os.getenv('WEB_SEARCH_TIMEOUT', '10'))

def _web_search(query: str, max_results: int = 5) -> str:
    """ค้นหาข้อมูลจากอินเทอร์เน็ตด้วย DuckDuckGo"""
    import concurrent.futures
    try:
        from ddgs import DDGS

        def _do_search():
            results = []
            with DDGS(timeout=int(_WEB_SEARCH_TIMEOUT)) as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(
                        f"**{r['title']}**\n{r['body']}\nที่มา: {r['href']}"
                    )
            return results

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_search)
            try:
                results = future.result(timeout=_WEB_SEARCH_TIMEOUT + 2)
            except concurrent.futures.TimeoutError:
                logger.warning(f"[web_search] timeout after {_WEB_SEARCH_TIMEOUT}s for query: {query!r}")
                return "การค้นหาใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง"

        if not results:
            return "ไม่พบผลลัพธ์การค้นหา"
        return "\n\n---\n\n".join(results)
    except Exception as e:
        logger.warning(f"[web_search] error: {e}", exc_info=True)
        return "ไม่สามารถค้นหาข้อมูลได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง"
```

**ผลกระทบ:** Web search จะไม่ block thread เกิน `WEB_SEARCH_TIMEOUT` วินาที (default 10 วินาที, configurable via `.env`) ไม่กระทบ tool อื่น
**ลำดับ:** 5

---

### H2 — `stream_response` ไม่มี exception handling

**หลักฐาน:** `agents/base_agent.py:31-47`

**Code ที่มีปัญหา:**
```python
# agents/base_agent.py:31-47
def stream_response(self, message, history=None, max_tokens=8000):
    messages = [...]
    stream = self.client.chat.completions.create(   # ถ้า throw ที่นี่ — uncaught
        model=self.model,
        messages=messages,
        max_tokens=max_tokens,
        stream=True
    )
    for chunk in stream:   # ถ้า throw ที่นี่ — uncaught
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

**ปัญหา:**
`stream_response` ถูกเรียกจาก PM subtask loop (`app.py:433`) ซึ่งไม่มี `try/except` รอบ call นั้น ถ้า `RateLimitError`, `APITimeoutError` หรือ `APIError` เกิดขึ้นระหว่าง streaming มันจะ bubble up ไปถึง outer `try/except` ที่ `app.py:456` แต่ตอนนั้น `pending_file` SSE events สำหรับ subtask ก่อนหน้าได้ถูก yield ออกไปแล้ว ทำให้ frontend มี `pendingTempPaths` ที่มี path บางส่วนแต่ไม่ครบ และ `subtask_done` ไม่ถูก emit ทำให้ UI ค้างในสถานะ typing

**วิธีแก้:**
เพิ่ม exception handling ใน `stream_response` ให้ yield error event แทน:

```python
# agents/base_agent.py:31-47 — แก้ใหม่
def stream_response(self, message, history=None, max_tokens=8000):
    """Simple streaming without tools."""
    messages = [
        {"role": "system", "content": self.system_prompt},
        *(history or []),
        {"role": "user", "content": message}
    ]
    try:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except GeneratorExit:
        raise   # ให้ Python จัดการ generator cleanup ตามปกติ
    except Exception as e:
        logger.error(f"[{self.name}] stream_response error: {e}", exc_info=True)
        raise   # re-raise เพื่อให้ caller จัดการ (PM loop จะ catch ด้วย try/except)
```

และเพิ่ม `try/except` ใน PM subtask loop ที่ `app.py:432-444`:

```python
# app.py:432-444 — แก้ PM subtask loop
subtask_chunks = []
try:
    for chunk in sub_agent.stream_response(f"[PM_SUBTASK]\n{sub_task_desc}", max_tokens=10000):
        yield format_sse({'type': 'text', 'content': chunk})
        subtask_chunks.append(chunk)
except Exception as sub_e:
    logger.error(f"[PM subtask {i+1}] stream_response failed: {sub_e}", exc_info=True)
    yield format_sse({'type': 'error', 'message': f'Subtask {i+1} ({sub_agent.name}) เกิดข้อผิดพลาด: กรุณาลองใหม่อีกครั้ง'})
    yield format_sse({'type': 'subtask_done', 'agent': sub_agent_type, 'index': i, 'total': len(subtasks)})
    continue   # ดำเนิน subtask ถัดไปต่อ แทนที่จะหยุดทั้งหมด
```

**ผลกระทบ:** PM task จะยังทำงานต่อได้แม้ subtask ใดสักตัวล้มเหลว และ UI จะได้รับ error message ที่ชัดเจนแทนที่จะค้าง ไม่กระทบ single-agent flow
**ลำดับ:** 3

---

### H3 — Partial document เข้า pending confirmation หลัง error

**หลักฐาน:** `index.html:1881-1888`

**Code ที่มีปัญหา:**
```javascript
// index.html:1881-1888 — done handler
} else if (receivedAgentEvent && !wasPMTask && lastAgent && lastAgent !== 'chat' && outputText) {
  // Single-agent: new document generated, waiting for confirm
  pendingDoc = outputText;
  pendingAgent = lastAgent;
  pendingFormat = 'md';
  isPendingConfirmation = true;
  _updateInputHint(true, 0);
}
```

**ปัญหา:**
condition ตรวจแค่ `outputText` truthy แต่ไม่ตรวจว่า error event ถูก emit หรือไม่ ถ้า stream บางส่วนแล้ว error (เช่น API timeout กลางคัน) outputText จะมีข้อความไม่สมบูรณ์ แต่ก็ยังถูก set เป็น `pendingDoc` ทำให้ผู้ใช้กด "บันทึก" แล้วได้ไฟล์ที่ขาดหาย

**วิธีแก้:**
เพิ่ม tracking flag `hadError` และ check ก่อน set pending:

```javascript
// index.html — เพิ่ม flag ข้าง outputText declaration (ประมาณบรรทัด 1693)
let outputText = '';
let hadError = false;   // <-- เพิ่ม

// index.html — error handler ตั้ง flag
} else if (data.type === 'error') {
    hadError = true;   // <-- เพิ่มบรรทัดนี้ก่อน _setInlineError
    _setInlineError(currentOutputEl, `เกิดข้อผิดพลาด: ${data.message}`);
    // ... (ส่วนที่เหลือเหมือนเดิม)

// index.html — done handler แก้ condition
} else if (receivedAgentEvent && !wasPMTask && lastAgent && lastAgent !== 'chat' && outputText && !hadError) {
  pendingDoc = outputText;
  pendingAgent = lastAgent;
  pendingFormat = 'md';
  isPendingConfirmation = true;
  _updateInputHint(true, 0);
}
```

**ผลกระทบ:** ป้องกัน partial document ถูก set เป็น pendingDoc เมื่อ error เกิดขึ้นระหว่าง stream ไม่มีผลต่อ happy path
**ลำดับ:** 6

---

### H4 — `global WORKSPACE_PATH` ใน `set_workspace_api` แก้ local binding

**หลักฐาน:** `app.py:471,476`

**Code ที่มีปัญหา:**
```python
# app.py:469-477
@app.route('/api/workspace', methods=['POST'])
def set_workspace_api():
    global WORKSPACE_PATH   # <-- ปัญหาอยู่ตรงนี้
    new_path = (request.json or {}).get('path', '').strip()
    abs_path = _normalize_workspace_path(new_path)
    if len(abs_path) <= 3 or not _is_allowed_workspace_path(abs_path): return jsonify({'error': 'Invalid path'}), 400
    os.makedirs(abs_path, exist_ok=True)
    with _workspace_lock: WORKSPACE_PATH = abs_path   # แก้แค่ local binding ใน app.py
    return jsonify({'path': abs_path, 'exists': True})
```

**ปัญหา:**
`WORKSPACE_PATH` ถูก import มาจาก `core.shared` ด้วย `from core.shared import ... WORKSPACE_PATH ...` (app.py:20-23) การทำ `global WORKSPACE_PATH` ใน function แล้ว assign จะแก้ module-level name ใน `app.py` เท่านั้น แต่ `core.shared.WORKSPACE_PATH` (ที่ทุก module อื่น เช่น `generate()` function ใช้ผ่าน `with _workspace_lock: workspace = WORKSPACE_PATH`) จะไม่ถูกอัพเดท ทำให้ workspace change มีผลเฉพาะในสาย code ที่อ่านจาก `app.WORKSPACE_PATH` แต่ `generate()` ยังคงใช้ค่าเดิมจาก `core.shared` เพราะอ่านจาก local name binding

เช่นเดียวกันที่ `create_workspace_folder` `app.py:496,502`

**วิธีแก้:**
ใช้ `core.shared.set_workspace()` ที่มี `global WORKSPACE_PATH` อยู่ใน module ที่ถูกต้อง:

```python
# app.py:469-477 — แก้ set_workspace_api
@app.route('/api/workspace', methods=['POST'])
def set_workspace_api():
    # ลบ: global WORKSPACE_PATH
    from core import shared as _shared
    new_path = (request.json or {}).get('path', '').strip()
    abs_path = _normalize_workspace_path(new_path)
    if len(abs_path) <= 3 or not _is_allowed_workspace_path(abs_path): return jsonify({'error': 'Invalid path'}), 400
    os.makedirs(abs_path, exist_ok=True)
    _shared.set_workspace(abs_path)   # <-- ใช้ setter ที่ถูกต้อง
    return jsonify({'path': abs_path, 'exists': True})

# app.py:494-503 — แก้ create_workspace_folder เช่นกัน
@app.route('/api/workspace/new', methods=['POST'])
def create_workspace_folder():
    # ลบ: global WORKSPACE_PATH
    from core import shared as _shared
    data = request.json or {}
    root, name = data.get('root', '').strip(), data.get('name', '').strip()
    if not root or not name or not re.match(r'^[a-zA-Z0-9_-]{1,50}$', name): return jsonify({'error': 'Invalid request'}), 400
    new_path = os.path.realpath(os.path.join(root, name))
    os.makedirs(new_path, exist_ok=True)
    _shared.set_workspace(new_path)   # <-- ใช้ setter ที่ถูกต้อง
    return jsonify({'path': new_path, 'name': name})
```

หมายเหตุ: `core.shared.set_workspace()` มี `_workspace_lock` ครอบอยู่แล้ว ดังนั้นไม่ต้องเขียน lock ซ้ำ

**ผลกระทบ:** Workspace change จะมีผลต่อทุก request ที่ตามมาจริงๆ ไม่ใช่แค่ instance ของ app.py ที่อ่าน local name
**ลำดับ:** 4

---

### H5 — `GeneratorExit` ไม่ถูก handle ใน `stream_response` และ `run_with_tools`

**หลักฐาน:** `agents/base_agent.py:39-47` และ `64-71`

**Code ที่มีปัญหา:**
```python
# agents/base_agent.py:39-47 — ไม่มี try/finally
stream = self.client.chat.completions.create(...)
for chunk in stream:
    if chunk.choices and ...:
        yield chunk.choices[0].delta.content
# stream ไม่ถูก close() ถ้า generator ถูก interrupt

# agents/base_agent.py:64-71 — เช่นกัน
stream = self.client.chat.completions.create(...)
for chunk in stream:
    ...
```

**ปัญหา:**
เมื่อ client disconnect (browser tab ปิด, user cancel) Flask จะ throw `GeneratorExit` เข้า generator ระหว่าง `yield` ถ้าไม่มี `try/finally` เพื่อ close HTTP stream กับ OpenRouter จะเกิด resource leak — connection ยังค้างอยู่ใน connection pool จนกว่า timeout จะเกิดขึ้น

**วิธีแก้:**
ใช้ `try/finally` รอบ stream loop ในทั้ง 2 method:

```python
# agents/base_agent.py:39-47 — stream_response แก้ใหม่
stream = self.client.chat.completions.create(
    model=self.model,
    messages=messages,
    max_tokens=max_tokens,
    stream=True
)
try:
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
finally:
    stream.close()   # คืน connection กลับ pool เสมอ

# agents/base_agent.py:64-71 — run_with_tools loop แก้ใหม่
stream = self.client.chat.completions.create(
    model=self.model,
    max_tokens=max_tokens,
    messages=messages,
    tools=tools,
    tool_choice="auto",
    stream=True
)
try:
    for chunk in stream:
        ...
finally:
    stream.close()
```

**ผลกระทบ:** ป้องกัน connection leak เมื่อ client disconnect กลางคัน ทำให้ connection pool ไม่หมดเมื่อมี concurrent user จำนวนมาก
**ลำดับ:** 7

---

### H6 — `copyOutput()` copy แค่ subtask สุดท้ายใน PM task

**หลักฐาน:** `index.html:1944-1952`

**Code ที่มีปัญหา:**
```javascript
// index.html:1944-1952
function copyOutput() {
    const outputs = document.querySelectorAll('.output-area');
    const text = outputs.length ? outputs[outputs.length - 1].textContent : '';
    navigator.clipboard.writeText(text).then(() => { ... });
}
```

**ปัญหา:**
`querySelectorAll('.output-area')` จะ select ทั้ง PM card bodies (`pm-agent-card-body output-area`) และ standalone output areas ด้วย จากนั้นเอาแค่ element สุดท้าย (`outputs[outputs.length - 1]`) ทำให้ copy ได้แค่ subtask สุดท้ายของ PM task แทนที่จะได้ทั้งหมด

**วิธีแก้:**
รวม text content จาก output areas ทั้งหมดใน AI message container ล่าสุด:

```javascript
// index.html:1944-1952 — แก้ใหม่
function copyOutput() {
    // หา AI message container ล่าสุด
    const containers = document.querySelectorAll('.msg-ai-container');
    if (!containers.length) return;
    const lastContainer = containers[containers.length - 1];
    const outputs = lastContainer.querySelectorAll('.output-area');
    const text = Array.from(outputs)
      .map(el => el.textContent.trim())
      .filter(Boolean)
      .join('\n\n---\n\n');
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      const btn = document.getElementById('copyBtn');
      const orig = btn.innerHTML;
      btn.innerHTML = '<span class="material-symbols-outlined" style="font-size:13px">check</span> คัดลอกแล้ว';
      setTimeout(() => btn.innerHTML = orig, 2000);
    });
}
```

**ผลกระทบ:** ผู้ใช้จะ copy output ครบทุก subtask ของ PM task ไม่กระทบ single-agent copy (ยังทำงานเหมือนเดิม)
**ลำดับ:** 8

---

### M1 — N+1 Queries ใน `db.get_history`

**หลักฐาน:** `db.py:210-238`

**Code ที่มีปัญหา:**
```python
# db.py:210-238
def get_history(limit: int = 50) -> list:
    with _connect() as conn:
        jobs = conn.execute(
            "SELECT ... FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()

        result = []
        for job in jobs:                    # loop N jobs
            files = conn.execute(           # query 1 ครั้งต่อ job = N queries
                "SELECT ... FROM saved_files WHERE job_id = ? ...",
                (job['id'],)
            ).fetchall()
            result.append({**dict(job), 'files': [dict(f) for f in files]})
        return result
```

**ปัญหา:**
ถ้า `limit=50` จะเกิด 51 queries (1 + 50) แทนที่จะเป็น 2 queries (jobs + files) ถ้า history page โหลดบ่อยและ DB มีข้อมูลมาก จะเกิด latency และ lock contention บน SQLite

**วิธีแก้:**
ใช้ JOIN หรือ IN clause เพื่อดึง files ทั้งหมดใน 1 query:

```python
# db.py:210-238 — แก้ใหม่
def get_history(limit: int = 50) -> list:
    """Return recent jobs with their saved files. Returns [] on any error."""
    if not DB_AVAILABLE:
        return []
    try:
        with _connect() as conn:
            jobs = conn.execute(
                """SELECT id, created_at, session_id, user_input,
                          agent, reason, status, output_text
                   FROM jobs
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()

            if not jobs:
                return []

            job_ids = [j['id'] for j in jobs]
            placeholders = ','.join('?' * len(job_ids))
            all_files = conn.execute(
                f"""SELECT job_id, filename, agent, size_bytes, created_at
                    FROM saved_files
                    WHERE job_id IN ({placeholders})
                    ORDER BY created_at""",
                job_ids
            ).fetchall()

            # Group files by job_id
            files_by_job = {}
            for f in all_files:
                files_by_job.setdefault(f['job_id'], []).append(dict(f))

            return [
                {**dict(job), 'files': files_by_job.get(job['id'], [])}
                for job in jobs
            ]

    except Exception as e:
        logger.warning(f"[db] get_history failed: {e}")
        return []
```

**ผลกระทบ:** ลด N+1 queries เป็น 2 queries เสมอ ไม่ว่า `limit` จะเป็นเท่าไร latency จะคงที่ ไม่กระทบ API contract
**ลำดับ:** 9

---

### M2 — `OPENROUTER_API_KEY` ไม่มี startup validation

**หลักฐาน:** `core/shared.py:9,41-45`

**Code ที่มีปัญหา:**
```python
# core/shared.py:9
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")   # อาจเป็น None

# core/shared.py:41-45
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,   # ส่ง None ได้ — OpenAI client รับ None โดยไม่ error
    timeout=_TIMEOUT,
)
```

**ปัญหา:**
`OpenAI(api_key=None)` ไม่ throw exception ตอน init แต่จะ throw `AuthenticationError` ตอน API call จริงๆ ทำให้ developer ที่ลืมตั้ง `.env` ต้องรอจนกว่าจะ send message แรกถึงจะรู้ว่า config ผิด

**วิธีแก้:**
เพิ่ม validation ทันทีหลัง load:

```python
# core/shared.py — เพิ่มหลังบรรทัด 9
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

import logging as _logging
_startup_logger = _logging.getLogger(__name__)

if not OPENROUTER_API_KEY:
    _startup_logger.error(
        "[shared] OPENROUTER_API_KEY is not set. "
        "Copy .env.example to .env and set your key. "
        "All API calls will fail until this is fixed."
    )
```

หมายเหตุ: ไม่ raise exception ตรงนี้เพราะ test scripts บางตัวอาจ import module นี้โดยไม่ต้องการ API key จริง การ log error level เพียงพอให้ developer เห็น

**ผลกระทบ:** Developer เห็น error ทันทีตอน startup log ไม่ต้องรอ request แรก
**ลำดับ:** 10

---

### M3 — `reader.cancel()` ขาดใน catch block

**หลักฐาน:** `index.html:1923-1941`

**Code ที่มีปัญหา:**
```javascript
// index.html:1923-1941
} catch (err) {
    _setInlineError(currentOutputEl, `ไม่สามารถเชื่อมต่อ server ได้: ${err.message}`);
    // ... UI cleanup ...
    // ไม่มี reader.cancel() — ReadableStream ยังค้างอยู่
}
```

**ปัญหา:**
เมื่อ error เกิดขึ้น (fetch fail, HTTP error, JSON parse error) `reader` ที่ได้จาก `response.body.getReader()` ยังไม่ถูก cancel ทำให้ browser ยังคง read stream ต่อในพื้นหลัง และ network connection ยังไม่ถูก close จนกว่า stream จะ end เอง

**วิธีแก้:**
ย้าย reader ออกมา scope ที่ใหญ่กว่า และ cancel ใน catch:

```javascript
// index.html — แก้ในส่วน sendMessage
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
let outputText = '';
let totalChars = 0;
let saveFailed = false;
let receivedAgentEvent = false;
let hadError = false;

try {
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        // ... (existing parsing logic)
    }
} catch (streamErr) {
    reader.cancel().catch(() => {});   // <-- เพิ่ม cancel
    throw streamErr;   // re-throw ให้ outer catch จัดการ UI
}

// outer catch block เพิ่ม:
} catch (err) {
    if (reader) {
        try { reader.cancel(); } catch (_) {}   // <-- เพิ่ม
    }
    _setInlineError(currentOutputEl, `ไม่สามารถเชื่อมต่อ server ได้: ${err.message}`);
    // ... (UI cleanup เหมือนเดิม)
}
```

**ผลกระทบ:** Network resource ถูก release ทันทีเมื่อ error เกิด ไม่มี dangling stream ค้างในพื้นหลัง
**ลำดับ:** 11

---

### M4 — `handle_pm_save` ดึง agent type จากชื่อไฟล์ fragile

**หลักฐาน:** `app.py:308`

**Code ที่มีปัญหา:**
```python
# app.py:308
db.record_file(job_id, filename, filename.split('_')[0], size)
#                                ^^^^^^^^^^^^^^^^^^^^^^^^^^
#                                agent = first part of filename
```

**ปัญหา:**
filename pattern คือ `{agent_type}_{slug}_{timestamp}.{ext}` เช่น `hr_leave_request_20250326_143022.md` การ split ด้วย `_` แล้วเอาส่วนแรกจะได้ `hr` ซึ่งถูกต้องในกรณีทั่วไป แต่ถ้า `_suggest_filename()` สร้างชื่อที่ขึ้นต้นด้วยตัวเลขหรือ pattern เปลี่ยนไปในอนาคต จะ break โดยไม่มี error ชัดเจน

**วิธีแก้:**
ส่ง `sub_agent_type` จาก PM loop เข้ามาใน `handle_pm_save` ผ่าน metadata แทน:

```python
# app.py — แก้ handle_pm_save signature
def handle_pm_save(temp_paths: list, workspace: str, job_id=None, output_format: str = 'md', output_formats: list = None, agent_types: list = None):
    saved = []
    for i, temp_path in enumerate(temp_paths):
        fmt = (output_formats[i] if output_formats and i < len(output_formats) else output_format)
        agent_type = (agent_types[i] if agent_types and i < len(agent_types) else filename.split('_')[0])
        # ...
        db.record_file(job_id, filename, agent_type, size)   # ใช้ agent_type จาก parameter

# app.py — PM loop yield pending_file พร้อม agent info
yield format_sse({'type': 'pending_file', 'temp_path': temp_path, 'filename': os.path.basename(temp_path), 'agent': sub_agent_type})
# frontend เก็บ agent ไว้ใน pendingFileAgents = []

# index.html — เพิ่ม state variable
let pendingFileAgents = [];

# index.html — pending_file handler
} else if (data.type === 'pending_file') {
    pendingTempPaths.push(data.temp_path);
    pendingFileAgents.push(data.agent || '');   # <-- เพิ่ม
}

# index.html — ส่ง agent_types ไปกับ request
if (pendingTempPaths.length > 0) {
    reqBody.pending_temp_paths = pendingTempPaths;
    reqBody.agent_types = pendingFileAgents;   # <-- เพิ่ม
    // ...
}

# app.py — /api/chat รับ agent_types
agent_types = request.json.get('agent_types')

# app.py — ส่งต่อไป handle_pm_save
for sse in handle_pm_save(pending_temp_paths, workspace, job_id, output_format, output_formats, agent_types): yield sse
```

**ผลกระทบ:** `db.record_file` จะได้รับ agent type ที่ถูกต้องเสมอ ไม่ขึ้นกับ filename pattern ที่อาจเปลี่ยน
**ลำดับ:** 12

---

### M5 — ไม่มี size limit บน `pending_doc`

**หลักฐาน:** `app.py:341,349-352`

**Code ที่มีปัญหา:**
```python
# app.py:341
pending_doc = request.json.get('pending_doc', '').strip()

# app.py:349-352
conversation_history = [
    {'role': m['role'], 'content': str(m['content'])[:3000]}   # history content มี cap ที่ 3000
    for m in (raw_history[-20:] ...)
]
# แต่ pending_doc ไม่มี cap เลย
```

**ปัญหา:**
`pending_doc` ถูกส่งกลับมาจาก frontend ทุก request เพื่อ handle save/edit/discard flow แต่ไม่มีการจำกัดขนาด ถ้า AI สร้างเอกสารขนาดใหญ่มาก (เช่น 500KB) และ frontend ส่งกลับมาใน request body ทุกครั้ง จะทำให้ memory usage สูงและ request parsing ช้า นอกจากนี้ JSON parse ของ request ที่ใหญ่มากอาจทำให้ latency เพิ่ม

**วิธีแก้:**
เพิ่ม size cap บน `pending_doc` และ content ใน conversation_history:

```python
# app.py — เพิ่ม constant
_MAX_PENDING_DOC_BYTES = int(os.getenv('MAX_PENDING_DOC_BYTES', str(200 * 1024)))  # 200KB default

# app.py:341 — แก้ pending_doc extraction
pending_doc_raw = request.json.get('pending_doc', '').strip()
pending_doc = pending_doc_raw[:_MAX_PENDING_DOC_BYTES] if pending_doc_raw else ''
if len(pending_doc_raw) > _MAX_PENDING_DOC_BYTES:
    logger.warning(f"[chat] pending_doc truncated from {len(pending_doc_raw)} to {_MAX_PENDING_DOC_BYTES} bytes")
```

**ผลกระทบ:** ป้องกัน memory spike จาก large pending_doc การ truncate อาจทำให้เอกสารที่ถูก truncate บันทึกไม่ครบ แต่กรณีนี้หายาก (เอกสาร >200KB) และ log จะแจ้งเตือน
**ลำดับ:** 13

---

### L1 — `pmSubtaskIndex` dead variable

**หลักฐาน:** ค้นหาใน `index.html` ทั้งไฟล์แล้วไม่พบ variable ชื่อ `pmSubtaskIndex`

**สถานะ:** NOT CONFIRMED — variable นี้อาจถูก remove ออกไปแล้วใน commit ก่อนหน้า ไม่ต้องดำเนินการ

---

## Execution Order (ลำดับที่แนะนำในการ fix)

| ลำดับ | Bug | ไฟล์ที่แก้ | เหตุผล |
|-------|-----|-----------|--------|
| 1 | C1 — save keyword false positive | `app.py`, `index.html` | CRITICAL — กระทบ core flow โดยตรง |
| 2 | C2 — PM output ไม่เข้า history | `index.html` | CRITICAL — กระทบ conversation context |
| 3 | H2 — PM loop ไม่มี try/except | `agents/base_agent.py`, `app.py` | HIGH — ทำให้ UI ค้างเมื่อ error |
| 4 | H4 — global WORKSPACE_PATH ผิด module | `app.py` | HIGH — workspace change ไม่มีผลจริง |
| 5 | H1 — web_search ไม่มี timeout | `core/utils.py` | HIGH — thread block |
| 6 | H3 — partial doc เข้า pending | `index.html` | HIGH — data integrity |
| 7 | H5 — GeneratorExit ไม่ handle | `agents/base_agent.py` | HIGH — resource leak |
| 8 | H6 — copyOutput แค่ subtask สุดท้าย | `index.html` | HIGH — UX |
| 9 | M1 — N+1 queries | `db.py` | MEDIUM — performance |
| 10 | M2 — API key ไม่มี startup check | `core/shared.py` | MEDIUM — DX |
| 11 | M3 — reader.cancel ขาด | `index.html` | MEDIUM — resource |
| 12 | M4 — agent type จากชื่อไฟล์ fragile | `app.py`, `index.html` | MEDIUM — maintainability |
| 13 | M5 — ไม่มี size limit pending_doc | `app.py` | MEDIUM — safety |

---

## หมายเหตุสำหรับ Implementer

1. Fix ลำดับ 1 (C1) และ 2 (C2) ต้องทำพร้อมกัน เพราะทั้งคู่เปลี่ยน behavior ของ state ที่ frontend ส่งมา
2. Fix ลำดับ 3 (H2) ต้องแก้ทั้ง `base_agent.py` และ `app.py` พร้อมกัน — แยก commit ได้แต่ต้อง deploy พร้อมกัน
3. Fix ลำดับ 12 (M4) เป็น breaking change เล็กน้อย — frontend ต้องส่ง `agent_types` ด้วย ถ้า frontend เก่าส่ง request มาโดยไม่มี `agent_types` ให้ fallback ไปใช้ `filename.split('_')[0]` เหมือนเดิม (backward compatible)
4. หลังแก้ทุก fix ให้รัน `./venv/bin/python3 smoke_test_phase0.py` และ `PYTHONUTF8=1 ./venv/bin/python3 test_cases.py` ก่อน commit
5. Bump version เป็น `v0.15.0` ใน `index.html` และ `CHANGELOG.md`
6. รัน `backend-python-reviewer` subagent ก่อน commit ตาม CLAUDE.md กฎเหล็ก
