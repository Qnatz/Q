import os
import sys
import chromadb
from chromadb.config import Settings

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.prompt_manager import PromptManager
from memory.unified_memory import UnifiedMemory, TinyDBManager, ChromaDBManager

CHROMADB_PATH = "data/storage/chromadb"
CHROMADB_COLLECTION_NAME = "prompts"

def check_chroma_status():
    print(f"Connecting to ChromaDB at: {CHROMADB_PATH}")
    
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient(path=CHROMADB_PATH, settings=Settings(allow_reset=True))
        
        # Get the collection
        collection = chroma_client.get_or_create_collection(name=CHROMADB_COLLECTION_NAME)
        
        # Initialize managers
        tinydb_manager = TinyDBManager(db_path=os.path.join(CHROMADB_PATH, "tinydb.json"))
        chromadb_manager = ChromaDBManager(collection=collection)
        
        # Initialize UnifiedMemory
        unified_memory = UnifiedMemory(tinydb_manager=tinydb_manager, chromadb_manager=chromadb_manager)
        
        # Initialize PromptManager
        prompt_manager = PromptManager(unified_memory=unified_memory)
        
        # Get all prompts
        all_prompts = prompt_manager.get_all_prompts()
        
        if all_prompts and all_prompts['ids']:
            print("\nAvailable prompts in ChromaDB:")
            for name in sorted(all_prompts['ids']):
                print(f"- {name}")
        else:
            print("\nNo prompts found in ChromaDB.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("This might indicate a problem with the ChromaDB setup or connection.")

if __name__ == "__main__":
    check_chroma_status()
