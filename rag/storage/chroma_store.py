import chromadb
from chromadb.config import Settings
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, db_path: str = None):
        db_path = db_path or os.path.join(os.getcwd(), "chroma_db")
        os.makedirs(db_path, exist_ok=True)

        try:
            self.client = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
            self.collection = self.client.get_or_create_collection(
                "docs", metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"VectorStore initialized at {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize VectorStore: {e}")
            raise

    def add_doc(self, doc_id: str, text: str, embedding: list, metadata: dict = None):
        try:
            self.collection.upsert(
                documents=[text],
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata] if metadata else None,
            )
            logger.debug(f"Upserted document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")

    def search(self, query_embedding: list, top_k: int = 5) -> List[Dict]:
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "distances", "metadatas"],
            )
            return [
                {"content": doc, "distance": dist, "metadata": meta}
                for doc, dist, meta in zip(
                    results["documents"][0],
                    results["distances"][0],
                    results["metadatas"][0],
                )
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def clear_collection(self):
        try:
            self.client.delete_collection(name="docs")
            self.collection = self.client.get_or_create_collection(
                "docs", metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection 'docs' cleared and recreated.")
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB collection: {e}")
            raise
