# agent_manager.py
import logging
logger = logging.getLogger(__name__)

from agent_processes.ideation_module import IdeationModule
from agent_processes.management_module import ManagementModule
from agent_processes.planning_module import PlanningModule
from agent_processes.programming_module import ProgrammingModule
from agent_processes.qa_module import QAModule
from agent_processes.research_module import ResearchModule
from agent_processes.review_module import ReviewModule
from agent_processes.code_assist_module import CodeAssistModule
from core.llm_service import LLMService
from core.settings import settings
from memory.prompt_manager import PromptManager
from qllm.config import Config
from qllm.unified_llm import UnifiedLLM
from tools.tool_registry import create_default_tool_registry
from memory.unified_memory import UnifiedMemory # Import UnifiedMemory
from core.project_context import ProjectContext # Import ProjectContext
from core.state_manager import StateManager # Import StateManager


class AgentManager:
    def __init__(self, unified_memory: UnifiedMemory, state_manager: StateManager): # Add unified_memory and state_manager as arguments
        self.logger = logging.getLogger(__name__)
        self._validate_config()
        self.unified_memory = unified_memory
        self.state_manager = state_manager

        try:
            self.unified_llm = self._initialize_llm()
            self.tool_registry = create_default_tool_registry(llm=self.unified_llm)
            self.prompt_manager = PromptManager(unified_memory=unified_memory) # Pass unified_memory
            self.llm_service = LLMService(self.unified_llm, self.prompt_manager)
            self.project_context = ProjectContext(project_data_source=unified_memory) # Pass unified_memory as project_data_source

            self._initialize_agents() # Call to initialize agents
        except Exception as e:
            self.logger.error(f"Failed to initialize AgentManager: {e}")
            raise

    def _validate_config(self):
        """Validate configuration parameters"""
        if not settings.llama_endpoint.startswith(("http://", "https://")):
            raise ValueError(f"Invalid llama endpoint: {settings.llama_endpoint}")

    def _initialize_llm(self) -> UnifiedLLM:
        """Initialize the LLM with proper configuration"""
        config = Config(
            backend="http" if settings.llm_mode == "offline" else "gemini",
            api_base=settings.llama_endpoint,
            model="llama",
            api_key=settings.api_key, # Pass the API key
        )
        return UnifiedLLM(cfg=config)

    def _initialize_agents(self):
        agent_configs = {
            "planner": (PlanningModule, [self.llm_service, self.prompt_manager, self.project_context]), # Pass project_context
            "manager": (ManagementModule, [self.llm_service, self.prompt_manager]),
            "programmer": (ProgrammingModule, [self.llm_service, self.prompt_manager, self.tool_registry, self.state_manager]),
            "qa": (QAModule, [self.tool_registry]),  # QAModule has different constructor
            "reviewer": (ReviewModule, [self.llm_service, self.prompt_manager, self.tool_registry]),
            "researcher": (ResearchModule, [self.llm_service, self.prompt_manager]),
            "ideator": (IdeationModule, [self.llm_service, self.prompt_manager]),
            "code_assist": (CodeAssistModule, [self.llm_service, self.prompt_manager]),
        }
        
        for name, (agent_class, params) in agent_configs.items():
            try:
                setattr(self, name, agent_class(*params))
            except Exception as e:
                print(f"Error initializing agent {name}: {e}")

    def get_agent(self, agent_name: str):
        """Safely retrieve an agent by name"""
        agent = getattr(self, agent_name, None)
        if agent is None:
            raise AttributeError(f"Agent '{agent_name}' not found")
        return agent
