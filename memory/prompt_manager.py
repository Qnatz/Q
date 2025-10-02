from memory.unified_memory import UnifiedMemory, MemoryType
from typing import Optional, Dict, Any, List

class PromptManager:
    def __init__(self, unified_memory: UnifiedMemory = None):
        self.unified_memory = unified_memory or UnifiedMemory()

    def add_prompt(self, name: str, content: str, metadata: Optional[Dict] = None):

        return self.unified_memory.store_prompt(name, content, metadata)

    def get_prompt(self, name: str) -> Optional[str]:

        prompt = self.unified_memory.get_prompt(name)

        return prompt

    def get_all_prompts(self) -> Dict[str, Any]:
        return self.unified_memory.get_all_prompts()