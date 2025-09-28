from memory.unified_memory import UnifiedMemory, MemoryType
from typing import Optional, Dict, List

class PromptManager:
    def __init__(self, unified_memory: UnifiedMemory = None):
        self.unified_memory = unified_memory or UnifiedMemory()

    def add_prompt(self, name: str, content: str, metadata: Optional[Dict] = None):

        return self.unified_memory.store_prompt(name, content, metadata)

    def get_prompt(self, name: str) -> Optional[str]:

        prompt = self.unified_memory.get_prompt(name)

        return prompt

    def get_all_prompts(self) -> Dict[str, List[str]]:
        results = self.unified_memory.query(query=None, memory_types=[MemoryType.PROMPT], user_id="system", top_k=1000) # Retrieve all prompts

        
        prompt_ids = []
        prompt_contents = []
        for res in results:
            if res["metadata"].get("type") == MemoryType.PROMPT.value:
                prompt_ids.append(res["metadata"].get("prompt_name", "unknown"))
                prompt_contents.append(res["content"])
        
        return {"ids": prompt_ids, "contents": prompt_contents}