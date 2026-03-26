import json
import logging
import re
from core.shared import get_client, get_model
from core.utils import execute_tool, format_sse

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self, name, system_prompt):
        self.name = name
        self.system_prompt = system_prompt
        self.client = get_client()
        self.model = get_model()

    def stream_response(self, message, history=None, max_tokens=8000):
        """Simple streaming without tools."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            *(history or []),
            {"role": "user", "content": message}
        ]
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def run_with_tools(self, user_message, workspace, tools, history=None, max_tokens=8000, max_iterations=5):
        """Agentic loop with tools (yields dicts for app.py to format as SSE)."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            *(history or []),
            {"role": "user", "content": user_message}
        ]

        web_search_calls = 0
        MAX_WEB_SEARCH_CALLS = 3

        for iteration in range(max_iterations):
            text_streamed = ""
            tool_calls_acc = {}

            stream = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=True
            )

            for chunk in stream:
                if not chunk.choices: continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    text_streamed += delta.content
                    yield {"type": "text", "content": delta.content}
                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.id: tool_calls_acc[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name: tool_calls_acc[idx]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments: tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

            if not tool_calls_acc:
                return

            tool_calls_list = [
                {
                    "id": tool_calls_acc[i]["id"],
                    "type": "function",
                    "function": {
                        "name": tool_calls_acc[i]["name"],
                        "arguments": tool_calls_acc[i]["arguments"]
                    }
                }
                for i in sorted(tool_calls_acc.keys())
            ]

            messages.append({"role": "assistant", "content": text_streamed or None, "tool_calls": tool_calls_list})

            allowed_names = {t['function']['name'] for t in tools}
            for tc in tool_calls_list:
                tool_name = tc["function"]["name"]
                if tool_name not in allowed_names:
                    yield {"type": "error", "message": f"Blocked disallowed tool: {tool_name}"}
                    return
                
                try:
                    args = json.loads(tc["function"]["arguments"])
                except:
                    yield {"type": "error", "message": "Invalid tool arguments"}
                    return

                # Status updates
                if tool_name == 'web_search':
                    web_search_calls += 1
                    if web_search_calls > MAX_WEB_SEARCH_CALLS:
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": "Search limit reached"})
                        continue
                    yield {"type": "status", "message": f"{self.name} กำลังค้นหา: {args.get('query','')[:50]}..."}
                elif tool_name in ('list_files', 'read_file'):
                    yield {"type": "status", "message": f"{self.name} กำลังอ่านข้อมูล..."}
                else:
                    yield {"type": "status", "message": f"{self.name} กำลังบันทึก: {tool_name}..."}

                # Execution via core.utils
                result = execute_tool(workspace, tool_name, args)
                
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                yield {"type": "tool_result", "tool": tool_name, "result": result[:200]}

            if text_streamed:
                return
