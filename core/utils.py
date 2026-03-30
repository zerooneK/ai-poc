import os
import re
import json
import logging
from datetime import datetime
from urllib.parse import urlparse
from mcp_server import fs_list_files, fs_create_file, fs_read_file, fs_update_file, fs_delete_file

logger = logging.getLogger(__name__)

_THAI_MONTHS = [
    'มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน',
    'กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'
]

try:
    from zoneinfo import ZoneInfo
    _BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
except Exception:
    logger.warning("inject_date: ZoneInfo('Asia/Bangkok') unavailable — falling back to local system time. Install 'tzdata' to fix this.")
    _BANGKOK_TZ = None

def inject_date(prompt: str) -> str:
    """Prepend today's date (Thai Buddhist calendar, Asia/Bangkok) to system prompt."""
    now = datetime.now(_BANGKOK_TZ) if _BANGKOK_TZ else datetime.now()
    date_str = f"{now.day} {_THAI_MONTHS[now.month - 1]} พ.ศ. {now.year + 543}"
    return f"วันที่ปัจจุบัน: {date_str}\n\n{prompt}"

def load_prompt(name: str) -> str:
    """Load Markdown content from a file in the 'prompts/' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "prompts", f"{name}.md")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ ไม่พบไฟล์ prompt: '{path}'")
        
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

_WEB_SEARCH_TIMEOUT = int(os.getenv('WEB_SEARCH_TIMEOUT', '15'))

def _web_search(query: str, max_results: int = 5) -> str:
    """ค้นหาข้อมูลจากอินเทอร์เน็ตด้วย DuckDuckGo"""
    try:
        from ddgs import DDGS
        results = []
        with DDGS(timeout=_WEB_SEARCH_TIMEOUT) as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"**{r['title']}**\n{r['body']}\nที่มา: {r['href']}"
                )
        if not results:
            return "ไม่พบผลลัพธ์การค้นหา"
        return "\n\n---\n\n".join(results)
    except Exception as e:
        logger.warning(f"[web_search] error: {e}", exc_info=True)
        return "ไม่สามารถค้นหาข้อมูลได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง"

_SOURCE_LINE_RE = re.compile(r'ที่มา:\s*(https?://\S+)')

def extract_web_sources(result: str) -> list:
    """Extract source URLs from a _web_search result string."""
    sources = []
    for url in _SOURCE_LINE_RE.findall(result):
        try:
            domain = urlparse(url).netloc
            sources.append({"url": url, "domain": domain})
        except Exception:
            pass
    return sources

def execute_tool(workspace: str, tool_name: str, tool_args: dict) -> str:
    """Execute a named MCP filesystem tool and return result string."""
    try:
        if tool_name == 'create_file':
            return fs_create_file(workspace, tool_args['filename'], tool_args['content'])
        elif tool_name == 'read_file':
            return fs_read_file(workspace, tool_args['filename'])
        elif tool_name == 'update_file':
            return fs_update_file(workspace, tool_args['filename'], tool_args['content'])
        elif tool_name == 'delete_file':
            return fs_delete_file(workspace, tool_args['filename'])
        elif tool_name == 'list_files':
            files = fs_list_files(workspace)
            if not files:
                return "workspace ว่างเปล่า ยังไม่มีไฟล์"
            return "\n".join(
                f"- {f['name']} ({f['size']} bytes, แก้ไขล่าสุด: {f['modified']})"
                for f in files
            )
        elif tool_name == 'local_delete':
            # ส่ง marker กลับ — app.py จะแปลงเป็น SSE event ให้ browser ลบจริง
            filename = tool_args.get('filename', '')
            return f"__LOCAL_DELETE__:{filename}"
        elif tool_name == 'web_search':
            query = tool_args.get('query', '')
            max_results = min(int(tool_args.get('max_results', 5)), 10)
            return _web_search(query, max_results)
        else:
            return f"❌ ไม่รู้จัก tool: {tool_name}"
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
        return f"❌ เกิดข้อผิดพลาดในการใช้ tool กรุณาลองใหม่"

def format_sse(data: dict) -> str:
    """Format a dictionary as an SSE data string."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
