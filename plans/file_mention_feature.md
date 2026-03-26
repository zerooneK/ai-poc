# Plan: @filename Mention — Attach Files to Agent Request
**Version target:** v0.11.0 (Minor bump — new UI capability + backend injection)
**Status:** Planned — not yet implemented
**Created:** 2026-03-25
**Depends on:** v0.10.0 (web_search) can be done independently — no dependency

---

## Goal
ให้ผู้ใช้สามารถพิมพ์ `@ชื่อไฟล์` ใน textarea เพื่อแนบไฟล์จาก workspace ให้ agent อ่านโดยอัตโนมัติ
โดยไม่ต้องพิมพ์ "แก้ไขไฟล์ X" และไม่ต้องรอให้ agent ตัดสินใจเรียก `read_file` เอง

ผลลัพธ์ที่ต้องการ:
- User พิมพ์ `@` → dropdown แสดงไฟล์ใน workspace
- เลือกไฟล์ → ชื่อไฟล์แสดงเป็น chip ในกล่องข้อความ
- กด Send → backend อ่านไฟล์และ inject เนื้อหาเข้า agent context โดยอัตโนมัติ
- Agent ตอบโดยมีบริบทจากไฟล์นั้นเต็มๆ ไม่ต้อง guess

---

## Architecture Decision

### วิธี inject ไฟล์เข้า agent

**Option A — Frontend fetch content → ส่ง content ใน reqBody**
Frontend เรียก `/api/file/content?filename=X` ก่อน send แล้วแนบ `[{filename, content}]` ใน reqBody

**Option B — Frontend ส่งแค่ชื่อไฟล์ → Backend อ่านและ inject (เลือกวิธีนี้ ✅)**
Frontend ส่ง `attached_files: ["file1.md", "file2.txt"]` ใน reqBody
Backend อ่านไฟล์และ prepend เนื้อหาเข้า user message ก่อนส่งให้ agent

เหตุผลที่เลือก Option B:
- ไม่มี large payload ใน HTTP request
- File access อยู่ server-side ตลอด (ปลอดภัยกว่า)
- ป้องกัน path traversal ได้ที่ backend
- ไม่ต้อง endpoint ใหม่

### วิธี inject เนื้อหาเข้า agent

ไม่ใช้ tool call (ช้า มีหลาย round-trip)
ใช้การ prepend ตรงๆ เข้า user message:

```
[ไฟล์ที่ผู้ใช้แนบมา]
--- contract_somchai_2025.md ---
<เนื้อหาไฟล์>
--- invoice_project_alpha.md ---
<เนื้อหาไฟล์>
[สิ้นสุดไฟล์แนบ]

คำขอ: <original user message>
```

ผลลัพธ์: agent เห็นเนื้อหาทันทีโดยไม่ต้องเรียก tool

---

## Implementation Steps

### Step 1 — Backend: รับ `attached_files` ใน `/api/chat`
**ไฟล์:** `app.py`
**ตำแหน่ง:** ต้น `chat()` function หลังจาก extract `conversation_history`

```python
# Extract attached files (filenames only — read server-side)
attached_filenames = request.json.get('attached_files', [])
attached_context = ''
if attached_filenames and isinstance(attached_filenames, list):
    parts = []
    for fname in attached_filenames[:5]:   # จำกัดสูงสุด 5 ไฟล์
        fname = str(fname).strip()
        if not fname:
            continue
        try:
            content = fs_read_file(workspace, fname)
            parts.append(f"--- {fname} ---\n{content}")
        except Exception as e:
            logger.warning(f"[attach] cannot read {fname}: {e}")
            parts.append(f"--- {fname} ---\n(ไม่สามารถอ่านไฟล์นี้ได้)")
    if parts:
        attached_context = (
            "[ไฟล์ที่ผู้ใช้แนบมา]\n" +
            "\n\n".join(parts) +
            "\n[สิ้นสุดไฟล์แนบ]\n\n"
        )
```

แล้ว prepend เข้า `user_input` ก่อนส่ง Orchestrator/agent:
```python
effective_input = attached_context + user_input
```

ใช้ `effective_input` แทน `user_input` ใน:
- Orchestrator messages
- PM Agent messages
- `run_agent_with_tools` call (single-agent)

### Step 2 — Backend: จำกัด max size ต่อไฟล์
**ไฟล์:** `app.py`

ใน loop อ่านไฟล์ ตัดเนื้อหาที่ยาวเกิน:
```python
MAX_ATTACH_CHARS = 8000   # ~2000 tokens ต่อไฟล์
content = fs_read_file(workspace, fname)
if len(content) > MAX_ATTACH_CHARS:
    content = content[:MAX_ATTACH_CHARS] + "\n...(ตัดทอนเนื้อหาเนื่องจากไฟล์ยาวเกินไป)"
```

### Step 3 — Backend: new endpoint `/api/files/list` (หรือใช้ของเดิม)
**ไม่ต้องเพิ่ม** — มี `/api/files` อยู่แล้ว (GET → list ไฟล์ใน workspace)
Frontend ใช้ข้อมูลจาก SSE stream (`/api/files/stream`) ที่มีอยู่แล้ว

### Step 4 — Frontend: เก็บ state ไฟล์ใน sidebar
**ไฟล์:** `index.html`

เพิ่ม state variable เก็บ list ไฟล์ปัจจุบัน (ให้ dropdown ใช้):
```javascript
let workspaceFiles = [];   // อัปเดตจาก SSE file events
```

ใน SSE handler ที่ process `type: 'files'` events เพิ่ม:
```javascript
workspaceFiles = data.files.map(f => f.name);   // ['contract.md', 'invoice.txt', ...]
```

### Step 5 — Frontend: เก็บ selected files state
**ไฟล์:** `index.html`

```javascript
let attachedFiles = [];   // ไฟล์ที่ user เลือกด้วย @mention
```

### Step 6 — Frontend: @ trigger + dropdown
**ไฟล์:** `index.html`

เพิ่ม dropdown HTML ใน `.input-wrapper` (ซ่อนไว้ก่อน):
```html
<div id="mentionDropdown" class="mention-dropdown" style="display:none"></div>
```

CSS สำหรับ dropdown:
```css
.mention-dropdown {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  right: 0;
  background: var(--surface-hi);
  border: 1px solid var(--outline-var);
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}
.mention-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: var(--on-surface);
}
.mention-item:hover, .mention-item.active {
  background: var(--primary);
  color: var(--on-primary);
}
.mention-item .material-symbols-outlined { font-size: 16px; }
```

JavaScript — ตรวจจับ `@` ใน textarea:
```javascript
let _mentionQuery = null;   // null = ไม่ได้อยู่ใน mention mode

textarea.addEventListener('input', () => {
  const val = textarea.value;
  const cursor = textarea.selectionStart;

  // หา @ ที่ใกล้กับ cursor ที่สุด
  const before = val.slice(0, cursor);
  const match = before.match(/@(\S*)$/);

  if (match) {
    _mentionQuery = match[1].toLowerCase();
    _showMentionDropdown(_mentionQuery);
  } else {
    _mentionQuery = null;
    _hideMentionDropdown();
  }
});

function _showMentionDropdown(query) {
  const filtered = workspaceFiles.filter(f =>
    f.toLowerCase().includes(query) &&
    !attachedFiles.includes(f)   // ไม่แสดงไฟล์ที่แนบไปแล้ว
  );
  const dd = document.getElementById('mentionDropdown');
  if (!filtered.length) { _hideMentionDropdown(); return; }

  dd.innerHTML = '';
  filtered.slice(0, 8).forEach((fname, i) => {
    const item = document.createElement('div');
    item.className = 'mention-item' + (i === 0 ? ' active' : '');
    item.innerHTML = `<span class="material-symbols-outlined">description</span>${_escapeHtml(fname)}`;
    item.onclick = () => _selectMention(fname);
    dd.appendChild(item);
  });
  dd.style.display = 'block';
}

function _hideMentionDropdown() {
  document.getElementById('mentionDropdown').style.display = 'none';
}

function _selectMention(fname) {
  // แทนที่ @query ด้วยชื่อไฟล์จริง แล้วลบออกจาก textarea
  const val = textarea.value;
  const cursor = textarea.selectionStart;
  const before = val.slice(0, cursor).replace(/@\S*$/, '');
  const after = val.slice(cursor);
  textarea.value = before + after;
  textarea.selectionStart = textarea.selectionEnd = before.length;

  // เพิ่มเข้า attachedFiles
  if (!attachedFiles.includes(fname)) {
    attachedFiles.push(fname);
    _renderAttachedChips();
  }
  _hideMentionDropdown();
  _mentionQuery = null;
  textarea.focus();
}
```

Keyboard nav (↑↓ Enter Escape) ใน dropdown:
```javascript
textarea.addEventListener('keydown', (e) => {
  const dd = document.getElementById('mentionDropdown');
  if (dd.style.display === 'none') return;

  const items = dd.querySelectorAll('.mention-item');
  const activeIdx = [...items].findIndex(el => el.classList.contains('active'));

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    const next = (activeIdx + 1) % items.length;
    items.forEach((el, i) => el.classList.toggle('active', i === next));
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    const prev = (activeIdx - 1 + items.length) % items.length;
    items.forEach((el, i) => el.classList.toggle('active', i === prev));
  } else if (e.key === 'Enter' && _mentionQuery !== null) {
    e.preventDefault();
    const active = dd.querySelector('.mention-item.active');
    if (active) active.click();
  } else if (e.key === 'Escape') {
    _hideMentionDropdown();
  }
});
```

### Step 7 — Frontend: แสดง chips ไฟล์ที่แนบ
**ไฟล์:** `index.html`

เพิ่ม chip container เหนือ textarea ใน `.input-container`:
```html
<div id="attachedChips" class="attached-chips" style="display:none"></div>
```

CSS:
```css
.attached-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px 12px 0;
}
.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--primary);
  color: var(--on-primary);
  border-radius: 12px;
  padding: 3px 10px 3px 8px;
  font-size: 12px;
  font-family: 'Sarabun', sans-serif;
}
.file-chip .chip-remove {
  cursor: pointer;
  font-size: 14px;
  opacity: 0.7;
  line-height: 1;
}
.file-chip .chip-remove:hover { opacity: 1; }
```

JavaScript:
```javascript
function _renderAttachedChips() {
  const container = document.getElementById('attachedChips');
  container.style.display = attachedFiles.length ? 'flex' : 'none';
  container.innerHTML = '';
  attachedFiles.forEach(fname => {
    const chip = document.createElement('div');
    chip.className = 'file-chip';
    chip.innerHTML = `
      <span class="material-symbols-outlined" style="font-size:13px">description</span>
      ${_escapeHtml(fname)}
      <span class="chip-remove material-symbols-outlined" onclick="_removeAttachedFile('${_escapeHtml(fname)}')">close</span>
    `;
    container.appendChild(chip);
  });
}

function _removeAttachedFile(fname) {
  attachedFiles = attachedFiles.filter(f => f !== fname);
  _renderAttachedChips();
}
```

### Step 8 — Frontend: ส่ง `attached_files` ใน reqBody
**ไฟล์:** `index.html`

ใน `sendMessage()` ใน `reqBody`:
```javascript
const reqBody = {
  message,
  session_id: _getSessionId(),
  output_format: resolvedFormat,
  conversation_history: conversationHistory.slice(-(MAX_HISTORY_TURNS * 2)),
  attached_files: [...attachedFiles]   // เพิ่มบรรทัดนี้
};
```

หลัง send ล้าง attached files:
```javascript
attachedFiles = [];
_renderAttachedChips();
```

### Step 9 — Frontend: ล้าง attached files เมื่อเปลี่ยน workspace
**ไฟล์:** `index.html`

ใน `_applyWorkspace()`:
```javascript
conversationHistory = [];
attachedFiles = [];          // เพิ่มบรรทัดนี้
_renderAttachedChips();      // เพิ่มบรรทัดนี้
```

### Step 10 — อัปเดต version และ docs
- `index.html`: v0.10.0 → v0.11.0 (หรือ v0.10.0 → v0.10.1 ถ้า web_search ยังไม่ merge)
- `CLAUDE.md`: เพิ่ม v0.11.0 ใน version history
- `CHANGELOG.md`: เพิ่ม entry v0.11.0
- `PROJECT_SUMMARY.md`: อัปเดต UI + agent capabilities
- `docs/poc-plan.md`: อัปเดต progress

---

## File Impact Summary

| ไฟล์ | สิ่งที่เปลี่ยน |
|---|---|
| `app.py` | extract `attached_files`, อ่านไฟล์ server-side, prepend context เข้า `effective_input` |
| `index.html` | state vars, SSE handler เก็บ file list, dropdown HTML/CSS/JS, chip HTML/CSS/JS, reqBody เพิ่ม `attached_files`, clear on send/workspace change |
| `CLAUDE.md` | version history |
| `CHANGELOG.md` | v0.11.0 entry |
| `PROJECT_SUMMARY.md` | UI + agent capabilities |
| `docs/poc-plan.md` | progress update |

---

## UX Flow (ตัวอย่าง)

```
User พิมพ์: "ช่วย@"
→ dropdown เปิด แสดงไฟล์ทั้งหมดใน workspace

User พิมพ์: "ช่วย@contract"
→ dropdown filter เหลือเฉพาะไฟล์ที่มีคำว่า "contract"

User กด Enter หรือ click ที่ไฟล์
→ @contract... หายไปจาก textarea
→ chip "contract_somchai_2025.md" โผล่เหนือ input

User พิมพ์ต่อ: "แก้ไขวันที่เริ่มงานเป็น 1 เมษายน 2568"
→ กด Send

Backend ได้รับ:
  message: "แก้ไขวันที่เริ่มงานเป็น 1 เมษายน 2568"
  attached_files: ["contract_somchai_2025.md"]

Backend inject:
  effective_input = """
  [ไฟล์ที่ผู้ใช้แนบมา]
  --- contract_somchai_2025.md ---
  <เนื้อหาสัญญาทั้งหมด>
  [สิ้นสุดไฟล์แนบ]

  แก้ไขวันที่เริ่มงานเป็น 1 เมษายน 2568
  """

Agent ตอบโดยมีบริบทสัญญาเต็ม ไม่ต้องเดา
```

---

## Edge Cases & Mitigations

| กรณี | การจัดการ |
|---|---|
| ไฟล์ที่แนบอ่านไม่ได้ (ถูกลบ) | แสดง `(ไม่สามารถอ่านไฟล์นี้ได้)` แทน crash |
| แนบไฟล์เกิน 5 ไฟล์ | จำกัด `[:5]` ใน backend พร้อม log warning |
| ไฟล์ใหญ่มาก (>8000 chars) | ตัดที่ 8000 + แจ้งว่าตัดทอน |
| User พิมพ์ `@ชื่อที่ไม่มีในระบบ` | dropdown ว่าง ไม่มี chip ไม่ส่ง attached_files |
| workspace ว่าง ไม่มีไฟล์ | dropdown ไม่แสดง (filtered list ว่าง) |
| แนบไฟล์ซ้ำ | ตรวจ `!attachedFiles.includes(fname)` ก่อนเพิ่ม |

---

## Out of Scope (ไม่ทำในรอบนี้)
- Drag & drop ไฟล์เข้า input
- Upload ไฟล์จากเครื่อง user
- Preview เนื้อหาไฟล์ก่อน send (hover tooltip)
- จำกัดชนิดไฟล์ที่แนบได้
- แนบไฟล์จาก workspace อื่น

---

## Risks

| ความเสี่ยง | ระดับ | แนวทางแก้ |
|---|---|---|
| Dropdown บัง input area ในบางขนาดหน้าจอ | ต่ำ | ใช้ `position: absolute; bottom: 100%` เปิดขึ้นบน |
| Context เต็มถ้าแนบหลายไฟล์ใหญ่ | กลาง | จำกัด 5 ไฟล์ + 8000 chars/ไฟล์ |
| Path traversal attack ผ่าน filename | ต่ำ | `fs_read_file` มี path validation อยู่แล้วใน mcp_server.py |
| UX ซับซ้อนเกินสำหรับ demo | ต่ำ | dropdown ง่าย ไม่มี state ซับซ้อน |

---

## Estimated Complexity
**ขนาดงาน:** กลาง
- Backend: แก้ `app.py` 1 จุด (ต้น `chat()` function) — ~30 บรรทัด
- Frontend: แก้ `index.html` หลายจุด — ~120 บรรทัด (HTML + CSS + JS)
- ไม่มี new file, ไม่มี DB change, ไม่มี endpoint ใหม่

**ความเสี่ยงต่อ stability:** ต่ำ–กลาง
- Backend เพิ่ม optional field — ถ้าไม่ส่ง `attached_files` ทุกอย่างทำงานเหมือนเดิม
- Frontend เพิ่ม UI component ใหม่ — ไม่แก้ส่วนที่มีอยู่ยกเว้น reqBody และ SSE handler
