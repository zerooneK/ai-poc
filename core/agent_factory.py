from agents.hr_agent import HRAgent
from agents.accounting_agent import AccountingAgent
from agents.manager_agent import ManagerAgent
from agents.pm_agent import PMAgent
from agents.chat_agent import ChatAgent

class AgentFactory:
    _agents = {}

    @classmethod
    def get_agent(cls, agent_type):
        """Get or create an agent instance (singleton-ish)."""
        agent_type = agent_type.lower().strip()
        if agent_type not in cls._agents:
            if agent_type == 'hr':
                cls._agents[agent_type] = HRAgent()
            elif agent_type == 'accounting':
                cls._agents[agent_type] = AccountingAgent()
            elif agent_type == 'manager':
                cls._agents[agent_type] = ManagerAgent()
            elif agent_type == 'pm':
                cls._agents[agent_type] = PMAgent()
            elif agent_type == 'chat':
                cls._agents[agent_type] = ChatAgent()
            else:
                # Default to chat for unknown types
                if 'chat' not in cls._agents:
                    cls._agents['chat'] = ChatAgent()
                return cls._agents['chat']
        
        return cls._agents[agent_type]
