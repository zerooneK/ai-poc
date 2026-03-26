import os
import json
import logging
from mcp_server import fs_list_files, fs_create_file, fs_read_file, fs_update_file, fs_delete_file

logger = logging.getLogger(__name__)

def load_prompt(name: str) -> str:
    """Load Markdown content from a file in the 'prompts/' directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "prompts", f"{name}.md")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ ไม่พบไฟล์ prompt: '{path}'")
        
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def _web_search(query: str, max_results: int = 5) -> str:
    """ค้นหาข้อมูลจากอินเทอร์เน็ตด้วย DuckDuckGo"""
    try:
        from ddgs import DDGS
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
        logger.warning(f"[web_search] error: {e}", exc_info=True)
        return "ไม่สามารถค้นหาข้อมูลได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง"

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
