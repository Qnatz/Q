# agent_manager.py
import os
import logging
from typing import Optional
from dataclasses import dataclass

from qllm.config import Config
from qllm.unified_llm import UnifiedLLM
from tools.tool_registry import create_default_tool_registry
from memory.prompt_manager import PromptManager

from agent_processes.planning_module import PlanningModule
from agent_processes.management_module import ManagementModule
from agent_processes.programming_module import ProgrammingModule
from agent_processes.qa_module import QAModule
from agent_processes.review_module import ReviewModule
from agent_processes.research_module import ResearchModule
from agent_processes.ideation_module import IdeationModule

@dataclass
class AgentConfig:
    """Configuration for agent initialization"""
    llm_mode: str = "offline"
    llama_endpoint: str = "http://127.0.0.1:8080"
    log_level: int = logging.INFO

class AgentManager:
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or self._load_default_config()
        if self.config.llm_mode is None:
            self.config.llm_mode = os.getenv("QAI_LLM_MODE", "offline")
        if self.config.llama_endpoint is None:
            self.config.llama_endpoint = os.getenv("QAI_LLAMA_ENDPOINT", "http://127.0.0.1:8080")
        if self.config.log_level is None:
            self.config.log_level = getattr(logging, os.getenv("QAI_LOG_LEVEL", "INFO"))

        self._setup_logging()
        self._validate_config()
        
        try:
            self.unified_llm = self._initialize_llm()
            self.tool_registry = create_default_tool_registry(llm=self.unified_llm)
            self.prompt_manager = PromptManager()
            self._initialize_agents()
        except Exception as e:
            self.logger.error(f"Failed to initialize AgentManager: {e}")
            raise

    def _load_default_config(self) -> AgentConfig:
        """Load configuration from environment variables with defaults"""
        return AgentConfig(
            llm_mode=os.getenv("QAI_LLM_MODE", "offline"),
            llama_endpoint=os.getenv("QAI_LLAMA_ENDPOINT", "http://127.0.0.1:8080"),
            log_level=getattr(logging, os.getenv("QAI_LOG_LEVEL", "INFO"))
        )

    def _setup_logging(self):
        """Configure logging with proper formatting"""
        logging.basicConfig(
            level=self.config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('agent_manager.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _validate_config(self):
        """Validate configuration parameters"""
        if not self.config.llama_endpoint.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid llama endpoint: {self.config.llama_endpoint}")

    def _initialize_llm(self) -> UnifiedLLM:
        """Initialize the LLM with proper configuration"""
        config = Config(
            backend="http" if self.config.llm_mode == "offline" else "gemini",
            api_base=self.config.llama_endpoint,
            model="llama"
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
            ("ideator", IdeationModule)
        ]
        
        for name, agent_class in agents_config:
            try:
                if name == "qa":
                    agent_instance = agent_class(llm=self.unified_llm, tool_registry=self.tool_registry)
                elif name == "ideator":
                    agent_instance = agent_class(self.unified_llm, self.prompt_manager, self.logger)
                elif name == "manager" or name == "researcher":
                    agent_instance = agent_class(self.unified_llm, self.prompt_manager)
                else:
                    agent_instance = agent_class(self.unified_llm, self.prompt_manager, self.tool_registry)
                
                setattr(self, name, agent_instance)
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