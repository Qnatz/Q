import logging
from typing import Dict, Optional

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
from memory.unified_memory import UnifiedMemory
from core.project_context import ProjectContext
from core.state_manager import StateManager


class AgentManager:
    def __init__(self, unified_memory: UnifiedMemory, state_manager: StateManager):
        self.logger = logging.getLogger(__name__)
        self._validate_config()
        self.unified_memory = unified_memory
        self.state_manager = state_manager
        
        # Track which agents failed to initialize
        self.failed_agents: Dict[str, str] = {}

        try:
            self.unified_llm = self._initialize_llm()
            self.prompt_manager = PromptManager(unified_memory=unified_memory)
            self.llm_service = LLMService(self.unified_llm, self.prompt_manager)
            self.tool_registry = create_default_tool_registry(llm=self.unified_llm, llm_service=self.llm_service)
            self.project_context = ProjectContext(project_data_source=unified_memory)

            self._initialize_agents()
        except Exception as e:
            self.logger.error(f"Failed to initialize AgentManager: {e}")
            raise

    def _validate_config(self):
        """Validate configuration parameters"""
        if not settings.llama_endpoint.startswith(("http://", "https://")):
            raise ValueError(f"Invalid llama endpoint: {settings.llama_endpoint}")

    def _initialize_llm(self) -> UnifiedLLM:
        """Initialize the LLM with proper configuration"""
        if settings.llm_mode == "offline":
            config = Config(
                backend="subprocess",
                model="all-MiniLM-L6-v2",
            )
        else:
            config = Config(
                backend="gemini",
                api_key=settings.api_key,
            )
        return UnifiedLLM(cfg=config)

    def _initialize_agents(self):
        """Initialize all agent modules with proper error tracking"""
        agent_configs = {
            "planner": (PlanningModule, [self.llm_service, self.prompt_manager, self.project_context]),
            "manager": (ManagementModule, [self.llm_service, self.prompt_manager]),
            "programmer": (ProgrammingModule, [self.llm_service, self.prompt_manager, self.tool_registry, self.state_manager]),
            "qa": (QAModule, [self.tool_registry]),
            "reviewer": (ReviewModule, [self.llm_service, self.prompt_manager, self.tool_registry]),
            "researcher": (ResearchModule, [self.llm_service, self.prompt_manager]),
            "ideator": (IdeationModule, [self.llm_service, self.prompt_manager]),
            "code_assist": (CodeAssistModule, [self.llm_service, self.prompt_manager, self.tool_registry, self.unified_memory]),
        }
        
        successfully_initialized = []
        
        for name, (agent_class, params) in agent_configs.items():
            try:
                agent_instance = agent_class(*params)
                setattr(self, name, agent_instance)
                successfully_initialized.append(name)
                self.logger.debug(f"Successfully initialized agent: {name}")
            except Exception as e:
                error_msg = f"Error initializing agent {name}: {e}"
                self.logger.error(error_msg)
                self.failed_agents[name] = str(e)
                # Set None instead of failing completely
                setattr(self, name, None)
        
        if self.failed_agents:
            self.logger.warning(
                f"Failed to initialize {len(self.failed_agents)} agents: "
                f"{', '.join(self.failed_agents.keys())}"
            )
        
        self.logger.info(
            f"AgentManager initialized with {len(successfully_initialized)}/{len(agent_configs)} agents"
        )

    def get_agent(self, agent_name: str):
        """Safely retrieve an agent by name with detailed error reporting"""
        if agent_name in self.failed_agents:
            error_msg = (
                f"Agent '{agent_name}' failed to initialize. "
                f"Error: {self.failed_agents[agent_name]}"
            )
            raise RuntimeError(error_msg)
        
        agent = getattr(self, agent_name, None)
        if agent is None:
            raise AttributeError(f"Agent '{agent_name}' not found or not initialized")
        
        return agent

    def is_agent_available(self, agent_name: str) -> bool:
        """Check if an agent is available and initialized"""
        return (
            agent_name not in self.failed_agents and 
            getattr(self, agent_name, None) is not None
        )

    def get_available_agents(self) -> list:
        """Get list of successfully initialized agents"""
        all_agents = [
            "planner", "manager", "programmer", "qa", 
            "reviewer", "researcher", "ideator", "code_assist"
        ]
        return [name for name in all_agents if self.is_agent_available(name)]

    def get_failed_agents(self) -> Dict[str, str]:
        """Get dictionary of failed agents and their error messages"""
        return self.failed_agents.copy()
