import json
import logging
from core.shared import get_client, get_model, ORCHESTRATOR_MAX_TOKENS
from core.utils import load_prompt, inject_date

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.client = get_client()
        self.model = get_model()
        self.prompt = load_prompt("orchestrator")

    def route(self, user_message, history=None):
        """Analyze user input and decide which agent to use."""
        messages = [
            {"role": "system", "content": inject_date(self.prompt)},
            *(history or []),
            {"role": "user", "content": user_message}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=ORCHESTRATOR_MAX_TOKENS,
                stream=False
            )
        except Exception as e:
            logger.warning("[Orchestrator] API error: %s — defaulting to chat", e)
            return "chat", "Orchestrator unavailable"
        
        try:
            content = response.choices[0].message.content
            if not content:
                return "chat", "Orchestrator returned empty response"
            result = json.loads(content)
            return result.get("agent", "chat"), result.get("reason", "")
        except (json.JSONDecodeError, KeyError, TypeError):
            return "chat", "Error parsing orchestrator response"
