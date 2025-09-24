from rag.storage.chroma_store import VectorStore

def main():
    print("Attempting to clear the knowledge base...")
    try:
        store = VectorStore()
        store.clear_collection()
        print("Knowledge base cleared successfully.")
    except Exception as e:
        print(f"Error clearing knowledge base: {e}")

if __name__ == "__main__":
    main()
