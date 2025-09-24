import os
import sys
import time

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.prompt_manager import PromptManager

PROMPT_DIR = "agent_prompts"

def ingest_prompts():
    loader = PromptManager()
    
    if not os.path.isdir(PROMPT_DIR):
        print(f"Error: Directory '{PROMPT_DIR}' not found.")
        return

    print(f"Starting ingestion from '{PROMPT_DIR}'...")
    for filename in os.listdir(PROMPT_DIR):
        if filename.endswith(".md"):
            prompt_name = filename.replace('.md', '')
            filepath = os.path.join(PROMPT_DIR, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                prompt_text = f.read()
            
            print(f"Ingesting prompt: {prompt_name}")
            start_time = time.time()
            loader.add_prompt(prompt_name, prompt_text)
            end_time = time.time()
            print(f"Ingested {prompt_name} in {end_time - start_time:.2f} seconds")
    time.sleep(1)

    print("\nIngestion complete. Verifying prompts in DB:")
    all_prompts = loader.get_all_prompts()
    
    if all_prompts and all_prompts['ids']:
        print(f"Successfully loaded {len(all_prompts['ids'])} prompts:")
        for name in all_prompts['ids']:
            print(f"- {name}")
    else:
        print("Could not verify prompts in the database.")

if __name__ == "__main__":
    ingest_prompts()

