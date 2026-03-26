import json
from core.shared import get_client, get_model
from core.utils import load_prompt

class Orchestrator:
    def __init__(self):
        self.client = get_client()
        self.model = get_model()
        self.prompt = load_prompt("orchestrator")

    def route(self, user_message, history=None):
        """Analyze user input and decide which agent to use."""
        messages = [
            {"role": "system", "content": self.prompt},
            *(history or []),
            {"role": "user", "content": user_message}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=1024,
            stream=False
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("agent", "chat"), result.get("reason", "")
        except (json.JSONDecodeError, KeyError):
            return "chat", "Error parsing orchestrator response"
