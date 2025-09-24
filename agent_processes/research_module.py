from typing import Dict, Any
from qllm.unified_llm import UnifiedLLM
from memory.prompt_manager import PromptManager # Import PromptManager

class ResearchModule:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager): # Accept prompt_manager
        self.llm = llm
        self.prompt_manager = prompt_manager # Store prompt_manager
        self.system_prompt_name = "orchestrator_research_phase_prompt.md" # Name of the prompt in memory

    def execute(self, task: Dict[str, Any]) -> str:
        system_prompt_content = self.prompt_manager.get_prompt(self.system_prompt_name)
        if not system_prompt_content:
            raise ValueError(f"System prompt '{self.system_prompt_name}' not found in memory.")

        prompt = (
            f"Task: {task}"
        )
        return self.llm.generate([{"role":"system","content":system_prompt_content}, {"role":"user","content":prompt}], use_tools=False)
