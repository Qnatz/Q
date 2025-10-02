import sys
from pathlib import Path

# Add the project root to sys.path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from memory.prompt_manager import PromptManager

prompt_manager = PromptManager()
all_prompts = prompt_manager.get_all_prompts()

if all_prompts and all_prompts['ids']:
    print("Available prompts in ChromaDB:")
    for name in all_prompts['ids']:
        print(f"- {name}")
else:
    print("No prompts found in ChromaDB.")