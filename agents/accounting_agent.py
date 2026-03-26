from agents.base_agent import BaseAgent
from core.utils import load_prompt

class AccountingAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Accounting Agent", system_prompt=load_prompt("accounting_agent"))
