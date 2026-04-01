import json
import logging
from agents.base_agent import BaseAgent
from core.utils import load_prompt

logger = logging.getLogger(__name__)

class PMAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="PM Agent", system_prompt=load_prompt("pm_agent"))

    def plan(self, user_message, history=None):
        """Decompose a complex request into subtasks."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            *(history or []),
            {"role": "user", "content": user_message}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=2048,
            stream=False
        )
        
        try:
            content = response.choices[0].message.content if response.choices else None
            if not content:
                return []
            result = json.loads(content)
            subtasks = result.get("subtasks", [])
            # Filter valid agents
            valid_agents = {'hr', 'accounting', 'manager'}
            return [s for s in subtasks if s.get('agent') in valid_agents]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError):
            return []
