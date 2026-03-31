from agents.base_agent import BaseAgent
from core.utils import load_prompt

class HRAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="HR Agent", system_prompt=load_prompt("hr_agent"))
