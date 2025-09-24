import chromadb
from chromadb.config import Settings

# Initialize the client with reset enabled
client = chromadb.PersistentClient(path="data/storage/chromadb", settings=Settings(allow_reset=True))

# Reset the database
print("Resetting the ChromaDB database...")
client.reset()
print("Database has been reset.")

# Verify by listing collections (should be empty)
collections = client.list_collections()
print("Current collections:", collections)
