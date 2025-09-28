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
from agent_processes.code_assist_module import CodeAssistAgent
from core.settings import settings
from memory.prompt_manager import PromptManager
from qllm.config import Config
from qllm.unified_llm import UnifiedLLM
from tools.tool_registry import create_default_tool_registry


class AgentManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._validate_config()

        try:
            self.unified_llm = self._initialize_llm()
            self.tool_registry = create_default_tool_registry(llm=self.unified_llm)
            self.prompt_manager = PromptManager()
            self.reviewer = ReviewModule(self.unified_llm, self.prompt_manager)
            self.code_assist = CodeAssistAgent(self.unified_llm, self.tool_registry, self.prompt_manager)
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
        """Initialize all specialized agents with error handling"""
        agents_config = [
            ("planner", PlanningModule),
            ("manager", ManagementModule),
            ("programmer", ProgrammingModule),
            ("qa", QAModule),
            ("reviewer", ReviewModule),
            ("researcher", ResearchModule),
            ("ideator", IdeationModule),
        ]

        for name, agent_class in agents_config:
            try:
                if name == "qa":
                    agent_instance = agent_class(
                        tool_registry=self.tool_registry
                    )
                elif name == "ideator":
                    agent_instance = agent_class(
                        self.unified_llm, self.prompt_manager
                    )
                elif name == "manager" or name == "researcher":
                    agent_instance = agent_class(self.unified_llm, self.prompt_manager)
                elif name == "planner":
                    agent_instance = agent_class(self.unified_llm, self.prompt_manager)
                else:
                    agent_instance = agent_class(
                        self.unified_llm, self.prompt_manager, self.tool_registry
                    )

                setattr(self, name, agent_instance);
                self.logger.info(f"Successfully initialized {name} agent")

            except Exception as e:
                self.logger.error(f"Failed to initialize {name} agent: {e}")
                raise

    def get_agent(self, agent_name: str):
        """Safely retrieve an agent by name"""
        agent = getattr(self, agent_name, None)
        if agent is None:
            raise AttributeError(f"Agent '{agent_name}' not found")
        return agent
