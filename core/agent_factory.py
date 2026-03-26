import logging
import threading
from agents.hr_agent import HRAgent
from agents.accounting_agent import AccountingAgent
from agents.manager_agent import ManagerAgent
from agents.pm_agent import PMAgent
from agents.chat_agent import ChatAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    _agents = {}
    _lock = threading.Lock()

    @classmethod
    def get_agent(cls, agent_type):
        """Get or create an agent instance (singleton-ish, thread-safe)."""
        agent_type = agent_type.lower().strip()
        if agent_type in cls._agents:          # fast path, no lock needed
            return cls._agents[agent_type]
        with cls._lock:
            if agent_type not in cls._agents:  # double-checked locking
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
                    logger.warning("[AgentFactory] Unknown agent_type %r, falling back to ChatAgent", agent_type)
                    if 'chat' not in cls._agents:
                        cls._agents['chat'] = ChatAgent()
                    return cls._agents['chat']
        return cls._agents[agent_type]
