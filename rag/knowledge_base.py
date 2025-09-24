from rag.embeddings.embedder_onnx import ONNXEmbedder
from rag.storage.chroma_store import VectorStore
from tools.folder_ingestion_tool import FolderIngestionTool
import uuid
import logging
from typing import List

logger = logging.getLogger(__name__)


class KnowledgeBase:  # Renamed class
    def __init__(
        self,
        embedder: ONNXEmbedder = None,
        vector_store: VectorStore = None,
    ):
        self.embedder = embedder or ONNXEmbedder()
        self.store = vector_store or VectorStore()
        self.folder_ingestion_tool = FolderIngestionTool()
        logger.info("KnowledgeBase initialized")

    def query(
        self, query: str, top_k: int = 5
    ) -> List[dict]:  # Renamed search to query
        try:
            q_embed = self.embedder.embed(query)
            results = [
                {
                    "document": doc.get("content"),
                    "distance": doc.get("distance"),
                    "metadata": doc.get("metadata"),
                }
                for doc in self.store.search(q_embed, top_k)
            ]
            return results
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []

    def add_document(self, doc_id: str, content: str, metadata: dict = None):
        try:
            embedding = self.embedder.embed(content)
            self.store.add_doc(doc_id, content, embedding, metadata)
            logger.debug(f"Added document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")

    def ingest(self, documents: list, metadata_list: list = None):
        metadata_list = metadata_list or [{}] * len(documents)
        for doc, metadata in zip(documents, metadata_list):
            self.add_document(str(uuid.uuid4()), doc, metadata)

    def ingest_folder(self, folder_path: str) -> int:
        try:
            result = self.folder_ingestion_tool.run(folder_path)
            if result.get("success"):
                logger.info(
                    f"Ingested {len(result['documents'])} documents from {folder_path}"
                )
                self.ingest(result["documents"], result.get("metadata", []))
                return len(result["documents"])
            logger.warning(f"Folder ingestion failed: {result.get('error')}")
            return 0
        except Exception as e:
            logger.error(f"Folder ingestion failed for {folder_path}: {e}")
            return 0

    def run(self, query: str) -> List[dict]:
        return self.query(query)  # Changed from search to query

    def get_contextual_response(self, query: str, conversation_history: list) -> str:
        """Enhanced RAG with conversation context"""
        # Augment query with last 2 conversation turns
        context_query = "\n".join(conversation_history[-2:] + [query])
        results = self.query(context_query)  # Changed from search to query

        # Format sources with citations
        sources = "\n".join(
            f"[{i+1}] {res['document']} (Source: {res['metadata'].get('source', 'unknown')})"
            for i, res in enumerate(results)
        )

        answer = (
            results[0]["document"] if results else "I don't have enough information"
        )
        return f"Based on my knowledge:\n\n{sources}\n\nAnswer: {answer}"
