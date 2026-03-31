from agents.base_agent import BaseAgent
from core.utils import load_prompt

class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Document Agent", system_prompt=load_prompt("document_agent"))
