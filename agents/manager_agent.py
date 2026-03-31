from agents.base_agent import BaseAgent
from core.utils import load_prompt

class ManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Manager Advisor", system_prompt=load_prompt("manager_agent"))
