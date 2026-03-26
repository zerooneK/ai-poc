from agents.base_agent import BaseAgent
from core.utils import load_prompt

class ChatAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Assistant", system_prompt=load_prompt("chat_agent"))
