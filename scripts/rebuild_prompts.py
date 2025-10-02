import os
import sys
import time
import chromadb
from chromadb.config import Settings

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.prompt_manager import PromptManager
from memory.unified_memory import UnifiedMemory, TinyDBManager, ChromaDBManager # Import UnifiedMemory and managers

PROMPT_DIR = "agent_prompts"
CHROMADB_PATH = "data/storage/chromadb"

# Define the collection name for ChromaDB
CHROMADB_COLLECTION_NAME = "prompts"

def clear_chromadb(client):
    print("Resetting the ChromaDB database...")
    client.reset()
    print("Database has been reset.")

def ingest_prompts(unified_memory_instance):
    loader = PromptManager(unified_memory=unified_memory_instance)
    
    if not os.path.isdir(PROMPT_DIR):
        print(f"Error: Directory '{PROMPT_DIR}' not found.")
        return

    print(f"Starting ingestion from '{PROMPT_DIR}'...")
    for root, _, files in os.walk(PROMPT_DIR):
        for filename in files:
            if filename.endswith(".md"):
                prompt_name = os.path.join(root, filename).replace(f"{PROMPT_DIR}/", "").replace(".md", "")
                filepath = os.path.join(root, filename)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    prompt_text = f.read()

                # MANUAL FIX: Surgically escape braces for the planning prompt
                if prompt_name == "orchestrator_planning_phase_prompt":
                    print("Applying manual brace escaping for planning prompt...")
                    prompt_text = prompt_text.replace('{', '{{').replace('}', '}}')
                    # Now, un-escape the actual placeholders
                    prompt_text = prompt_text.replace('{{FOLLOWUP_MESSAGE_PROMPT}}', '{FOLLOWUP_MESSAGE_PROMPT}')
                    prompt_text = prompt_text.replace('{{PROJECT_TITLE}}', '{PROJECT_TITLE}')
                    prompt_text = prompt_text.replace('{{REFINED_PROMPT}}', '{REFINED_PROMPT}')
                    prompt_text = prompt_text.replace('{{USER_REQUEST_PROMPT}}', '{USER_REQUEST_PROMPT}')
                    prompt_text = prompt_text.replace('{{GITHUB_WORKFLOWS_PERMISSIONS_PROMPT}}', '{GITHUB_WORKFLOWS_PERMISSIONS_PROMPT}')
                    prompt_text = prompt_text.replace('{{PLAN_SCHEMA}}', '{PLAN_SCHEMA}')
                    prompt_text = prompt_text.replace('{{SCRATCHPAD}}', '{SCRATCHPAD}')

                print(f"Ingesting prompt: {prompt_name}")
                start_time = time.time()
                loader.add_prompt(prompt_name, prompt_text)
                end_time = time.time()
                print(f"Ingested {prompt_name} in {end_time - start_time:.2f} seconds")

    print("\nIngestion complete. Verifying prompts in DB:")
    all_prompts = loader.get_all_prompts()
    
    if all_prompts and all_prompts['ids']:
        print(f"Successfully loaded {len(all_prompts['ids'])} prompts:")
        for name in all_prompts['ids']:
            print(f"- {name}")
        
        # Temporary: Verify manager_routing_prompt content
        manager_routing_content = unified_memory_instance.get_prompt("manager_routing_prompt")
        if manager_routing_content:
            print(f"\nContent of manager_routing_prompt:\n{manager_routing_content[:200]}...")
        else:
            print("\nmanager_routing_prompt not found after ingestion.")
    else:
        print("Could not verify prompts in the database.")

if __name__ == "__main__":
    # Initialize ChromaDB client once
    chroma_client = chromadb.PersistentClient(path=CHROMADB_PATH, settings=Settings(allow_reset=True))
    
    clear_chromadb(chroma_client)
    
    # Ensure the collection exists and get it
    collection = chroma_client.get_or_create_collection(name=CHROMADB_COLLECTION_NAME)
    # unified_memory.chromadb.ensure_collection_exists() # Collection is ensured by get_or_create_collection
    # Initialize managers
    tinydb_manager = TinyDBManager(db_path=os.path.join(CHROMADB_PATH, "tinydb.json")) # Use a specific path for TinyDB
    chromadb_manager = ChromaDBManager(collection=collection)
    
    # Initialize UnifiedMemory with manager instances
    unified_memory = UnifiedMemory(tinydb_manager=tinydb_manager, chromadb_manager=chromadb_manager)

    ingest_prompts(unified_memory)
