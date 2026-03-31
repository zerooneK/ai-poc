# Plan: Web Search Tool via DDGS
**Version target:** v0.10.0 (Minor bump — new agent capability)
**Library:** `duckduckgo-search` (DDGS)
**Status:** ✅ IMPLEMENTED — committed in v0.10.0 (2026-03-26)
**Created:** 2026-03-25

---

## Goal
ให้ HR / Accounting / Manager Advisor agents ค้นหาข้อมูลอินเทอร์เน็ตได้
เมื่อผู้ใช้ถามเรื่องที่ต้องการข้อมูลปัจจุบัน เช่น กฎหมายแรงงานล่าสุด อัตราภาษีใหม่ หรือแนวโน้มตลาด
โดยไม่ต้องใช้ API key เพิ่ม

---

## Why DDGS (not Tavily)
| ข้อ | DDGS | Tavily |
|---|---|---|
| API key | ไม่ต้องใช้ | ต้องใช้ |
| ค่าใช้จ่าย | ฟรีตลอด | Free tier 1,000/เดือน |
| Setup | `pip install` เดียว | สมัคร account + `.env` |
| Output | title + URL + snippet | AI summary พร้อมใช้ |
| Reliability | Unofficial scraping | Official API |
| POC fit | ดีมาก | ดี แต่ setup ซับซ้อนกว่า |

DDGS เหมาะกับ POC เพราะ LLM สามารถ synthesize จาก raw snippets ได้ดีอยู่แล้ว

---

## Scope

### ใช้กับ agent ไหน
| Agent | ได้รับ web_search | เหตุผล |
|---|---|---|
| HR Agent | ✅ | กฎหมายแรงงาน ค่าแรงขั้นต่ำ ข้อบังคับใหม่ |
| Accounting Agent | ✅ | อัตราภาษี VAT กฎหมายบัญชีล่าสุด |
| Manager Advisor | ✅ | เทรนด์การบริหาร benchmarks อุตสาหกรรม |
| PM Agent | ❌ | งาน PM เน้น structure ไม่ใช่ข้อมูล real-time |
| Orchestrator | ❌ | ทำหน้าที่ routing เท่านั้น |

---

## Implementation Steps

### Step 1 — เพิ่ม dependency
**ไฟล์:** `requirements.txt`

เพิ่ม:
```
duckduckgo-search
```

### Step 2 — สร้าง `web_search` tool function
**ไฟล์:** `app.py`

เพิ่มฟังก์ชันนี้ใน section เดียวกับ `_execute_tool`:

```python
def _web_search(query: str, max_results: int = 5) -> str:
    """ค้นหาข้อมูลจากอินเทอร์เน็ตด้วย DuckDuckGo"""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"**{r['title']}**\n{r['body']}\nที่มา: {r['href']}"
                )
        if not results:
            return "ไม่พบผลลัพธ์การค้นหา"
        return "\n\n---\n\n".join(results)
    except Exception as e:
        logger.warning(f"[web_search] error: {e}")
        return f"ไม่สามารถค้นหาข้อมูลได้: {str(e)}"
```

### Step 3 — เพิ่ม tool schema ใน MCP_TOOLS
**ไฟล์:** `app.py`

เพิ่มใน `MCP_TOOLS` list:

```python
{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "ค้นหาข้อมูลจากอินเทอร์เน็ต ใช้เมื่อผู้ใช้ถามเกี่ยวกับข้อมูลปัจจุบัน "
            "เช่น กฎหมายล่าสุด อัตราภาษี แนวโน้มตลาด ข่าวสาร หรือข้อมูลที่อาจเปลี่ยนแปลงบ่อย"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "คำค้นหาภาษาไทยหรือภาษาอังกฤษ"
                },
                "max_results": {
                    "type": "integer",
                    "description": "จำนวนผลลัพธ์สูงสุด (default 5, max 10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}
```

### Step 4 — เพิ่ม `web_search` ใน `READ_ONLY_TOOLS`
**ไฟล์:** `app.py`

แก้ `READ_ONLY_TOOLS` definition:

```python
READ_ONLY_TOOLS = [
    t for t in MCP_TOOLS
    if t['function']['name'] in ('list_files', 'read_file', 'web_search')
]
```

เหตุผล: `web_search` เป็น read-only (ไม่เขียนไฟล์) จึงอยู่ใน group เดียวกับ `read_file`

### Step 5 — เพิ่ม handler ใน `_execute_tool`
**ไฟล์:** `app.py`

เพิ่ม case ใน `_execute_tool`:

```python
elif tool_name == "web_search":
    query = tool_args.get("query", "")
    max_results = min(int(tool_args.get("max_results", 5)), 10)
    result = _web_search(query, max_results)
    return result
```

### Step 6 — อัปเดต status message ใน streaming
**ไฟล์:** `app.py`

ใน `run_agent_with_tools` ส่วนที่ generate status message:

```python
# เพิ่ม case สำหรับ web_search
if tool_name == 'web_search':
    query = tool_args.get('query', '')
    status_msg = f"กำลังค้นหา: {query[:50]}..."
elif tool_name in _read_tool_names:
    status_msg = "กำลังอ่านข้อมูล..."
else:
    status_msg = f"กำลังบันทึก: {tool_name}..."
```

### Step 7 — อัปเดต system prompts สำหรับ 3 agents
**ไฟล์:** `app.py`

เพิ่มใน HR / Accounting / Manager Advisor system prompts:

```
การใช้ web_search:
- ใช้เมื่อผู้ใช้ถามเกี่ยวกับข้อมูลที่อาจเปลี่ยนแปลง เช่น "กฎหมายล่าสุด", "อัตราปัจจุบัน", "ข่าวใหม่", "แนวโน้มล่าสุด"
- ใช้เมื่อผู้ใช้ระบุปีปัจจุบันหรือช่วงเวลาล่าสุดในคำขอ
- อย่าใช้สำหรับข้อมูลทั่วไปที่ไม่เปลี่ยนแปลง เช่น นิยาม หลักการพื้นฐาน
- หลังค้นหาแล้ว ให้อ้างอิง URL ที่มาในเอกสารด้วยเสมอ
- ค้นหาเป็นภาษาไทยก่อน ถ้าผลลัพธ์น้อยให้ลองภาษาอังกฤษ
```

### Step 8 — อัปเดต `setup.sh`
**ไฟล์:** `setup.sh`

ไม่ต้องแก้ เพราะ setup.sh ติดตั้งจาก `requirements.txt` อยู่แล้ว

### Step 9 — อัปเดต version และ docs
- `index.html`: v0.9.0 → v0.10.0
- `CLAUDE.md`: เพิ่ม v0.10.0 ใน version history
- `CHANGELOG.md`: เพิ่ม entry v0.10.0
- `PROJECT_SUMMARY.md`: เพิ่ม web_search ใน agent capabilities
- `docs/poc-plan.md`: อัปเดต progress

---

## File Impact Summary

| ไฟล์ | สิ่งที่เปลี่ยน |
|---|---|
| `requirements.txt` | เพิ่ม `duckduckgo-search` |
| `app.py` | `_web_search()`, tool schema, `_execute_tool`, `READ_ONLY_TOOLS`, 3 system prompts, status message |
| `index.html` | version bump → v0.10.0 |
| `CLAUDE.md` | version history |
| `CHANGELOG.md` | v0.10.0 entry |
| `PROJECT_SUMMARY.md` | agent capabilities table |
| `docs/poc-plan.md` | progress update |

---

## Risks & Mitigations

| ความเสี่ยง | ผลกระทบ | แนวทางแก้ |
|---|---|---|
| DuckDuckGo rate limit | ค้นหาไม่ได้ระหว่าง demo | `_web_search` return error message ภาษาไทยแทน crash |
| ผลลัพธ์ภาษาไทยไม่ครบ | ข้อมูลน้อย | prompt ให้ลองภาษาอังกฤษถ้าไทยได้น้อย |
| Agent ค้นหาทุก request โดยไม่จำเป็น | latency เพิ่ม | prompt ชัดเจน: ค้นเฉพาะข้อมูล real-time เท่านั้น |
| DDGS library เปลี่ยน API | break | pin version ใน requirements.txt |
| ผลลัพธ์ยาวเกิน context | token overflow | จำกัด max_results=5, snippet ต่อผล |

---

## Out of Scope (ไม่ทำในรอบนี้)
- PM Agent ไม่ได้รับ web_search
- ไม่เพิ่ม UI toggle ให้ user เปิด/ปิด search
- ไม่ cache ผลการค้นหา
- ไม่รองรับ image search หรือ news search แยก endpoint

---

## Estimated Complexity
**ขนาดงาน:** เล็ก–กลาง
- app.py แก้ใน 5 จุด (tool function, schema, execute handler, status msg, 3 prompts)
- ไม่มี DB change
- ไม่มี UI change นอกจาก version bump
- ไม่มี new file

**ความเสี่ยงต่อ stability:** ต่ำ — tool ใหม่ไม่กระทบ tool เดิม
