
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.prompt_manager import PromptManager
from memory.unified_memory import UnifiedMemory, TinyDBManager, ChromaDBManager
import chromadb
from chromadb.config import Settings

CHROMADB_PATH = "data/storage/chromadb"
CHROMADB_COLLECTION_NAME = "prompts"

def inspect_prompt(prompt_name):
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient(path=CHROMADB_PATH, settings=Settings(allow_reset=True))
        collection = chroma_client.get_or_create_collection(name=CHROMADB_COLLECTION_NAME)
        
        # Initialize managers
        tinydb_manager = TinyDBManager(db_path=os.path.join(CHROMADB_PATH, "tinydb.json"))
        chromadb_manager = ChromaDBManager(collection=collection)
        
        # Initialize UnifiedMemory
        unified_memory = UnifiedMemory(tinydb_manager=tinydb_manager, chromadb_manager=chromadb_manager)
        
        # Initialize PromptManager
        prompt_manager = PromptManager(unified_memory=unified_memory)
        
        prompt_content = prompt_manager.get_prompt(prompt_name)
        
        if prompt_content:
            print(f"--- Content of '{prompt_name}' ---")
            print(repr(prompt_content))
            print("--- End of Content ---")
        else:
            print(f"Prompt '{prompt_name}' not found.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_prompt(sys.argv[1])
    else:
        print("Please provide a prompt name to inspect.")
