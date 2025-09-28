import logging
from core.agent_manager import AgentManager
from core.llm_service import LLMService
from core.router import Router
from core.state_manager import StateManager
from core.workflow_manager import WorkflowManager
from core.response_handler import ResponseHandler
from core.context_builder import ContextBuilder
from memory.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class AgentInitializer:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.agent_manager = AgentManager()
        self.prompt_manager = PromptManager()
        self.llm_service = LLMService(self.agent_manager.unified_llm, self.prompt_manager)
        self.context_builder = ContextBuilder(self.llm_service)
        self.router = Router(self.agent_manager.unified_llm, self.agent_manager.prompt_manager)
        self.workflow_manager = WorkflowManager(
            self.planner, self.manager, self.programmer, self.qa, self.reviewer, self.state_manager
        )
        self.response_handler = ResponseHandler(
            self.agent_manager.unified_llm,
            state_manager,
            self.context_builder,
            self.workflow_manager,
            self.agent_manager.researcher,
            self.agent_manager.ideator,
            self.router,
            self.agent_manager,
            self.agent_manager.code_assist,
        )
