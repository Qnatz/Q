from typing import Dict, Any
import logging
from core.llm_service import LLMService
from memory.prompt_manager import PromptManager # Import PromptManager

logger = logging.getLogger(__name__)

class ResearchModule:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.system_prompt_name = "orchestrator/research"

    def execute(self, task: Dict[str, Any]) -> str:
        system_prompt_content = self.prompt_manager.get_prompt(self.system_prompt_name)
        if not system_prompt_content:
            logger.error(f"System prompt '{self.system_prompt_name}' not found in memory.")
            raise ValueError(f"System prompt '{self.system_prompt_name}' not found in memory.")

        prompt = (
            f"Task: {task}"
        )
        return self.llm_service.llm.generate([{"role":"system","content":system_prompt_content}, {"role":"user","content":prompt}], use_tools=False)
