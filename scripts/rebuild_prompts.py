import os
import sys
import time
import chromadb
from chromadb.config import Settings

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.prompt_manager import PromptManager
from memory.unified_memory import UnifiedMemory # Import UnifiedMemory

PROMPT_DIR = "agent_prompts"
CHROMADB_PATH = "data/storage/chromadb"

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

    print("\nIngestion complete. Verifying prompts in DB:")
    all_prompts = loader.get_all_prompts()
    
    if all_prompts and all_prompts['ids']:
        print(f"Successfully loaded {len(all_prompts['ids'])} prompts:")
        for name in all_prompts['ids']:
            print(f"- {name}")
    else:
        print("Could not verify prompts in the database.")

if __name__ == "__main__":
    # Initialize ChromaDB client once
    chroma_client = chromadb.PersistentClient(path=CHROMADB_PATH, settings=Settings(allow_reset=True))
    
    # Initialize UnifiedMemory once, passing the client
    unified_memory = UnifiedMemory(chromadb_client=chroma_client) # Pass client to UnifiedMemory

    clear_chromadb(chroma_client)
    unified_memory.chromadb.ensure_collection_exists()
    ingest_prompts(unified_memory)
