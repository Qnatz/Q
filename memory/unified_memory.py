# memory/unified_memory.py
"""
Unified Memory System - Bridges ChromaDB, TinyDB, and ONNX embeddings
Provides seamless integration between semantic and structured memory storage
"""

import os
import json
import hashlib
import numpy as np
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import time

import chromadb
from chromadb.config import Settings
import onnxruntime as ort
from transformers import AutoTokenizer
from tinydb import TinyDB, Query
from tinydb.operations import increment

import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class MemoryType(Enum):
    CONVERSATION = "conversation"
    SEMANTIC = "semantic" 
    FACT = "fact"
    STATE = "state"
    TOOL_RESULT = "tool_result"
    AGENT_OUTPUT = "agent_output"
    PROMPT = "prompt"

@dataclass
class MemoryEntry:
    id: str
    content: str
    type: MemoryType
    metadata: Dict[str, Any]
    timestamp: datetime
    user_id: str
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'type': self.type.value
        }

class ONNXEmbeddingEngine:
    """Fast local embeddings using ONNX runtime"""
    
    def __init__(self, model_path: str = "data/models/onnx/all-MiniLM-L6-v2"):
        self.model_path = Path(model_path)
        self.session = None
        self.tokenizer = None
        self.max_length = 512
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize ONNX model and tokenizer"""
        try:
            # Load ONNX model
            onnx_path = self.model_path / "model.onnx"
            if not onnx_path.exists():
                logger.warning(f"ONNX model not found at {onnx_path}. Using fallback embeddings.")
                return
            
            # Create ONNX Runtime session
            options = ort.SessionOptions()
            options.inter_op_num_threads = 1
            options.intra_op_num_threads = 1
            self.session = ort.InferenceSession(
                str(onnx_path),
                sess_options=options,
                providers=['CPUExecutionProvider']
            )
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            logger.info(f"ONNX embedding model loaded: {self.model_path}")
            
            
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            self.session = None
            self.tokenizer = None
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Generate embeddings for text(s)"""
        print(f"ONNXEmbeddingEngine: Encoding {len(texts)} text(s) ...")
        start_time = time.time()
        if self.session is None or self.tokenizer is None:
            # Fallback to simple hash-based embeddings for testing
            if isinstance(texts, str):
                texts = [texts]
            return np.array([self._fallback_embedding(text) for text in texts])
        
        if isinstance(texts, str):
            texts = [texts]
        
        # Tokenize
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="np"
        )
        
        # Run inference
        outputs = self.session.run(
            None,
            {
                "input_ids": encoded["input_ids"].astype(np.int64),
                "attention_mask": encoded["attention_mask"].astype(np.int64),
                "token_type_ids": encoded["token_type_ids"].astype(np.int64)
            }
        )
        
        # Mean pooling
        embeddings = self._mean_pooling(outputs[0], encoded["attention_mask"])
        end_time = time.time()
        print(f"ONNXEmbeddingEngine: Encoded {len(texts)} text(s) in {end_time - start_time:.2f} seconds")
        return embeddings
    
    def _mean_pooling(self, token_embeddings: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        """Apply mean pooling to token embeddings"""
        input_mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
        return sum_embeddings / sum_mask
    
    def _fallback_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Generate deterministic hash-based embedding for fallback"""
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            chunk = hash_bytes[i:i+4]
            if len(chunk) == 4:
                val = int.from_bytes(chunk, 'big') / (2**32)
                embedding.append(val - 0.5)  # Center around 0
        
        # Pad or truncate to desired dimension
        while len(embedding) < dim:
            embedding.extend(embedding[:min(len(embedding), dim - len(embedding))])
        
        return embedding[:dim]

class ChromaDBManager:
    """ChromaDB operations for semantic/vector memory"""
    
    def __init__(self, db_path: str = "data/storage/chromadb", client: Optional[chromadb.PersistentClient] = None):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        if client:
            self.client = client
        else:
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(anonymized_telemetry=False)
            )
        self.ensure_collection_exists()
        logger.info(f"ChromaDB initialized at: {self.db_path}")

    def ensure_collection_exists(self):
        self.collection = self.client.get_or_create_collection(
            name="qai_unified_memory",
            metadata={"description": "QAI Agent unified memory storage"}
        )
    
    def store(self, entry: MemoryEntry) -> str:
        """Store memory entry with embedding"""
        try:
            self.collection.upsert(
                ids=[entry.id],
                documents=[entry.content],
                embeddings=[entry.embedding] if entry.embedding else None,
                metadatas=[{
                    "type": entry.type.value,
                    "user_id": entry.user_id,
                    "timestamp": entry.timestamp.isoformat(),
                    **entry.metadata
                }]
            )
            logger.debug(f"Stored ChromaDB entry: {entry.id}")
            
            return entry.id
        except Exception as e:
            logger.error(f"Failed to store ChromaDB entry: {e}")
            return ""
    
    def similarity_search(self, query_text: str, top_k: int = 5, 
                         filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for similar content"""
        try:
            where_clause = filters or {}
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and results["metadatas"]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0], 
                    results["distances"][0] if results["distances"] else [0] * len(results["documents"][0])
                )):
                    formatted_results.append({
                        "content": doc,
                        "metadata": metadata,
                        "similarity": 1 - distance,  # Convert distance to similarity
                        "source": "chromadb"
                    })
            
            logger.debug(f"ChromaDB search returned {len(formatted_results)} results")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
    
    def get_by_type(
        self,
        memory_type: MemoryType,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get entries by type"""
        try:
            # Build simple where clause
            where_clause = {"type": memory_type.value}
            if user_id:
                where_clause = {"$and": [{"type": memory_type.value}, {"user_id": user_id}]}

            results = self.collection.get(
                where=where_clause,
                limit=limit
            )
            logger.debug(
                f"ChromaDBManager.get_by_type: Results from collection.get: {results}"
            )

            formatted_results = []
            if results.get("documents") and results.get("metadatas"):
                for doc, metadata in zip(results["documents"], results["metadatas"]):
                    # Double-check filter just in case
                    if user_id is None or metadata.get("user_id") == user_id:
                        formatted_results.append({
                            "content": doc,
                            "metadata": metadata,
                            "source": "chromadb"
                        })

            return formatted_results

        except Exception as e:
            logger.error(f"ChromaDBManager.get_by_type failed: {e}")
            return []


class TinyDBManager:
    """TinyDB operations for structured data and state management"""
    
    def __init__(self, db_path: str = "data/storage"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Multiple TinyDB tables for different data types
        self.history_db = TinyDB(self.db_path / "chat_history.json")
        self.facts_db = TinyDB(self.db_path / "facts.json")
        self.state_db = TinyDB(self.db_path / "system_state.json")
        
        # Table references
        self.history_table = self.history_db.table('conversations')
        self.facts_table = self.facts_db.table('facts')
        self.state_table = self.state_db.table('state')
        self.metrics_table = self.state_db.table('metrics')
        
        logger.info(f"TinyDB initialized at: {self.db_path}")
    
    def store_conversation(self, user_id: str, role: str, content: str, 
                          metadata: Optional[Dict] = None) -> str:
        """Store conversation turn"""
        try:
            entry_id = f"conv_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            entry = {
                "id": entry_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            self.history_table.insert(entry)
            self._update_metrics("conversations_stored", 1)
            logger.debug(f"Stored conversation: {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            return ""
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        try:
            User = Query()
            results = self.history_table.search(User.user_id == user_id)
            
            # Sort by timestamp and limit
            sorted_results = sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)
            return [{"content": r["content"], "metadata": r, "source": "tinydb"} 
                   for r in sorted_results[:limit]]
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def store_fact(self, key: str, value: Any, category: str = "general", 
                   user_id: str = "system") -> str:
        """Store structured fact"""
        try:
            fact_id = f"fact_{hashlib.md5(key.encode()).hexdigest()[:8]}"
            fact = {
                "id": fact_id,
                "key": key,
                "value": value,
                "category": category,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Upsert fact
            Fact = Query()
            if self.facts_table.search(Fact.key == key):
                self.facts_table.update(fact, Fact.key == key)
            else:
                self.facts_table.insert(fact)
            
            self._update_metrics("facts_stored", 1)
            logger.debug(f"Stored fact: {key}")
            return fact_id
            
        except Exception as e:
            logger.error(f"Failed to store fact: {e}")
            return ""
    
    def get_fact(self, key: str) -> Optional[Any]:
        """Retrieve fact by key"""
        try:
            Fact = Query()
            result = self.facts_table.search(Fact.key == key)
            return result[0]["value"] if result else None
            
        except Exception as e:
            logger.error(f"Failed to get fact: {e}")
            return None
    
    def search_facts(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search facts by content"""
        try:
            Fact = Query()
            
            # Build search conditions
            conditions = []
            if category:
                conditions.append(Fact.category == category)
            
            # Simple text search in key and value
            text_condition = (Fact.key.search(query, flags=re.IGNORECASE) | 
                            Fact.value.search(query, flags=re.IGNORECASE))
            conditions.append(text_condition)
            
            # Combine conditions
            if len(conditions) == 1:
                search_condition = conditions[0]
            else:
                search_condition = conditions[0]
                for condition in conditions[1:]:
                    search_condition = search_condition & condition
            
            results = self.facts_table.search(search_condition)
            return [{"content": f"{r['key']}: {r['value']}", 
                    "metadata": r, "source": "tinydb"} for r in results]
            
        except Exception as e:
            logger.error(f"Failed to search facts: {e}")
            return []
    
    def store_state(self, key: str, value: Any, user_id: str = "system") -> str:
        """Store system state"""
        try:
            state_id = f"state_{key}_{user_id}"
            state = {
                "id": state_id,
                "key": key,
                "value": value,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
            
            State = Query()
            if self.state_table.search((State.key == key) & (State.user_id == user_id)):
                self.state_table.update(state, (State.key == key) & (State.user_id == user_id))
            else:
                self.state_table.insert(state)
            
            logger.debug(f"Stored state: {key}")
            return state_id
            
        except Exception as e:
            logger.error(f"Failed to store state: {e}")
            return ""
    
    def get_state(self, key: str, user_id: str = "system") -> Optional[Any]:
        """Get system state"""
        try:
            State = Query()
            result = self.state_table.search((State.key == key) & (State.user_id == user_id))
            return result[0]["value"] if result else None
            
        except Exception as e:
            logger.error(f"Failed to get state: {e}")
            return None
    
    def _update_metrics(self, metric_name: str, increment_by: int = 1):
        """Update usage metrics"""
        try:
            Metric = Query()
            if self.metrics_table.search(Metric.name == metric_name):
                self.metrics_table.update(increment('value'), Metric.name == metric_name)
            else:
                self.metrics_table.insert({
                    "name": metric_name,
                    "value": increment_by,
                    "last_updated": datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")


class UnifiedMemory:
    """
    Unified Memory System - Main interface for all memory operations
    Bridges ChromaDB (semantic), TinyDB (structured), and ONNX (embeddings)
    """
    
    def __init__(self, 
                 chromadb_path: str = "data/storage/chromadb",
                 tinydb_path: str = "data/storage", 
                 onnx_model_path: str = "data/models/onnx/all-MiniLM-L6-v2",
                 chromadb_client: Optional[chromadb.PersistentClient] = None):
        
        self.embeddings = ONNXEmbeddingEngine(onnx_model_path)
        self.chromadb = ChromaDBManager(chromadb_path, client=chromadb_client)
        self.tinydb = TinyDBManager(tinydb_path)
        
        # Configuration
        self.auto_embed = True
        self.similarity_threshold = 0.7
        
        logger.info("UnifiedMemory system initialized")
    
    def store(self, content: str, memory_type: MemoryType, user_id: str = "default",
             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Universal store method - routes to appropriate storage backend(s)
        """
        metadata = metadata or {}
        timestamp = datetime.now()
        entry_id = self._generate_id(content, memory_type, user_id, timestamp)
        
        try:
            # Generate embedding if needed
            embedding = None
            if self.auto_embed and memory_type in [MemoryType.CONVERSATION,
                                                  MemoryType.SEMANTIC,
                                                  MemoryType.AGENT_OUTPUT,
                                                  MemoryType.TOOL_RESULT,
                                                  MemoryType.PROMPT]:
                embedding = self.embeddings.encode(content)[0].tolist()
            
            # Create memory entry
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                type=memory_type,
                metadata=metadata,
                timestamp=timestamp,
                user_id=user_id,
                embedding=embedding
            )
            
            # Store in appropriate backend(s)
            if memory_type == MemoryType.CONVERSATION:
                # Store in both TinyDB (structured) and ChromaDB (semantic)
                self.tinydb.store_conversation(user_id, 
                                             metadata.get("role", "unknown"), 
                                             content, metadata)
                if embedding:
                    self.chromadb.store(entry)
            
            elif memory_type == MemoryType.FACT:
                # Store in TinyDB as structured data
                key = metadata.get("key", f"fact_{entry_id}")
                category = metadata.get("category", "general")
                self.tinydb.store_fact(key, content, category, user_id)
                
            elif memory_type == MemoryType.STATE:
                # Store in TinyDB state table
                key = metadata.get("key", f"state_{entry_id}")
                self.tinydb.store_state(key, content, user_id)
                
            elif memory_type in [MemoryType.SEMANTIC, MemoryType.AGENT_OUTPUT, 
                               MemoryType.TOOL_RESULT, MemoryType.PROMPT]:
                # Store in ChromaDB for semantic search
                if embedding:
                    self.chromadb.store(entry)
            
            logger.debug(f"Stored {memory_type.value}: {entry_id}")
            
            return entry_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return ""
    
    def query(self, query: str, memory_types: Optional[List[MemoryType]] = None,
             user_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Universal query method - searches across all relevant backends
        """
        if memory_types is None:
            memory_types = [MemoryType.CONVERSATION, MemoryType.SEMANTIC, MemoryType.FACT]
        
        all_results = []
        
        try:
            # If query is empty, retrieve all entries of specified types
            if not query:
                for mt in memory_types:
                    if mt in [MemoryType.CONVERSATION, MemoryType.SEMANTIC, MemoryType.AGENT_OUTPUT, MemoryType.TOOL_RESULT, MemoryType.PROMPT]:
                        all_results.extend(self.chromadb.get_by_type(mt, user_id, top_k))
                    elif mt in [MemoryType.FACT]:
                        # TinyDB doesn't have a direct get_by_type that returns all facts
                        # without a search query, so we'll skip for now or add a new method
                        pass
                return all_results

            # ChromaDB semantic search
            if any(mt in [MemoryType.CONVERSATION, MemoryType.SEMANTIC, 
                         MemoryType.AGENT_OUTPUT, MemoryType.TOOL_RESULT, MemoryType.PROMPT] for mt in memory_types):
                
                filters = []
                if user_id:
                    filters.append({"user_id": user_id})
                if memory_types:
                    filters.append({"type": {"$in": [mt.value for mt in memory_types]}})
                
                where_clause = {}
                if len(filters) > 1:
                    where_clause["$and"] = filters
                elif filters:
                    where_clause = filters[0]

                semantic_results = self.chromadb.similarity_search(query, top_k, where_clause)
                all_results.extend(semantic_results)
            
            # TinyDB structured search
            if MemoryType.FACT in memory_types:
                fact_results = self.tinydb.search_facts(query)
                all_results.extend(fact_results)
            
            if MemoryType.CONVERSATION in memory_types and user_id:
                conv_results = self.tinydb.get_conversation_history(user_id, top_k)
                all_results.extend(conv_results)
            
            # Rank and merge results
            ranked_results = self._rank_and_merge_results(all_results, query, top_k)
            
            logger.debug(f"Query '{query}' returned {len(ranked_results)} results")
            
            return ranked_results
            
        except Exception as e:
            logger.error(f"Failed to query memory: {e}")
            return []
    
    def get_conversation_context(self, user_id: str, current_query: str, 
                               context_turns: int = 5, semantic_results: int = 3) -> Dict[str, Any]:
        """
        Get comprehensive conversation context for the orchestrator
        Combines recent conversation + relevant semantic memories
        """
        try:
            # Get recent conversation history
            recent_history = self.tinydb.get_conversation_history(user_id, context_turns)
            
            # Get semantically similar content
            semantic_context = self.chromadb.similarity_search(
                current_query, 
                semantic_results,
                filters={"user_id": user_id}
            )
            
            # Get relevant facts
            fact_context = self.tinydb.search_facts(current_query)[:2]
            
            return {
                "recent_conversation": recent_history,
                "semantic_context": semantic_context,
                "relevant_facts": fact_context,
                "context_summary": self._generate_context_summary(
                    recent_history, semantic_context, fact_context
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return {"recent_conversation": [], "semantic_context": [], "relevant_facts": []}
    
    def store_conversation_turn(self, user_id: str, role: str, content: str,
                              metadata: Optional[Dict] = None) -> str:
        """
        Convenience method for storing conversation turns
        Automatically handles both structured and semantic storage
        """
        enhanced_metadata = {
            "role": role,
            "turn_type": "conversation",
            **(metadata or {})
        }
        
        return self.store(content, MemoryType.CONVERSATION, user_id, enhanced_metadata)
    
    def store_agent_output(self, agent_name: str, output: str, user_id: str = "system",
                          metadata: Optional[Dict] = None) -> str:
        """
        Store output from specific agents for later retrieval and learning
        """
        enhanced_metadata = {
            "agent": agent_name,
            "output_type": "agent_response",
            **(metadata or {})
        }
        
        return self.store(output, MemoryType.AGENT_OUTPUT, user_id, enhanced_metadata)
    
    def store_tool_result(self, tool_name: str, result: str, user_id: str = "system",
                         metadata: Optional[Dict] = None) -> str:
        """
        Store tool execution results for context and learning
        """
        enhanced_metadata = {
            "tool": tool_name,
            "result_type": "tool_execution",
            **(metadata or {})
        }
        
        return self.store(result, MemoryType.TOOL_RESULT, user_id, enhanced_metadata)

    def store_prompt(self, name: str, content: str, metadata: Optional[Dict] = None) -> str:
        """
        Store a prompt in memory.
        """
        enhanced_metadata = {
            "prompt_name": name,
            **(metadata or {})
        }
        print(f"DEBUG: UnifiedMemory.store_prompt: Stored prompt '{name}'.")
        return self.store(content, MemoryType.PROMPT, user_id="system", metadata=enhanced_metadata)

    def get_prompt(self, name: str) -> Optional[str]:
        """
        Retrieve a prompt from memory by name.
        """
        try:
            prompt_name = name
            where_clause = {
                "prompt_name": prompt_name
            }
            results = self.chromadb.collection.get(
                where=where_clause,
                limit=1
            )
            if results and results.get("documents") and len(results["documents"]) > 0:
                return results["documents"][0]
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve prompt '{name}': {e}")
            return None

    def get_conversation_context(self, user_id: str, current_query: str, 
                               context_turns: int = 5, semantic_results: int = 3) -> Dict[str, Any]:
        """
        Get comprehensive conversation context for the orchestrator
        Combines recent conversation + relevant semantic memories
        """
        try:
            # Get recent conversation history
            recent_history = self.tinydb.get_conversation_history(user_id, context_turns)
            
            # Get semantically similar content
            semantic_context = self.chromadb.similarity_search(
                current_query, 
                semantic_results,
                filters={"user_id": user_id}
            )
            
            # Get relevant facts
            fact_context = self.tinydb.search_facts(current_query)[:2]
            
            return {
                "recent_conversation": recent_history,
                "semantic_context": semantic_context,
                "relevant_facts": fact_context,
                "context_summary": self._generate_context_summary(
                    recent_history, semantic_context, fact_context
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return {"recent_conversation": [], "semantic_context": [], "relevant_facts": []}
    
    def store_conversation_turn(self, user_id: str, role: str, content: str,
                              metadata: Optional[Dict] = None) -> str:
        """
        Convenience method for storing conversation turns
        Automatically handles both structured and semantic storage
        """
        enhanced_metadata = {
            "role": role,
            "turn_type": "conversation",
            **(metadata or {})
        }
        
        return self.store(content, MemoryType.CONVERSATION, user_id, enhanced_metadata)
    
    def store_agent_output(self, agent_name: str, output: str, user_id: str = "system",
                          metadata: Optional[Dict] = None) -> str:
        """
        Store output from specific agents for later retrieval and learning
        """
        enhanced_metadata = {
            "agent": agent_name,
            "output_type": "agent_response",
            **(metadata or {})
        }
        
        return self.store(output, MemoryType.AGENT_OUTPUT, user_id, enhanced_metadata)
    
    def store_tool_result(self, tool_name: str, result: str, user_id: str = "system",
                         metadata: Optional[Dict] = None) -> str:
        """
        Store tool execution results for context and learning
        """
        enhanced_metadata = {
            "tool": tool_name,
            "result_type": "tool_execution",
            **(metadata or {})
        }
        
        return self.store(result, MemoryType.TOOL_RESULT, user_id, enhanced_metadata)

    def _generate_id(self, content: str, memory_type: MemoryType, 
                    user_id: str, timestamp: datetime) -> str:
        """
        Generate unique ID for memory entry"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        time_str = timestamp.strftime('%Y%m%d_%H%M%S')
        return f"{memory_type.value}_{user_id}_{time_str}_{content_hash}"
    
    def _rank_and_merge_results(self, results: List[Dict[str, Any]], 
                               query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Rank and merge results from different sources"""
        if not results:
            return []
        
        # Simple ranking by similarity score and source priority
        source_weights = {"chromadb": 1.0, "tinydb": 0.8}
        
        for result in results:
            base_score = result.get("similarity", 0.5)
            source_weight = source_weights.get(result.get("source", "unknown"), 0.5)
            result["final_score"] = base_score * source_weight
        
        # Sort by score and return top_k
        ranked = sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)
        return ranked[:top_k]
    
    def _generate_context_summary(self, recent_history: List, semantic_context: List,
                                 fact_context: List) -> str:
        """
        Generate a brief summary of the available context"""
        summary_parts = []
        
        if recent_history:
            summary_parts.append(f"{len(recent_history)} recent conversation turns")
        
        if semantic_context:
            summary_parts.append(f"{len(semantic_context)} semantically relevant memories")
        
        if fact_context:
            summary_parts.append(f"{len(fact_context)} relevant facts")
        
        return f"Context: {', '.join(summary_parts)}" if summary_parts else "No context available"

# Convenience functions for backward compatibility
def get_unified_memory() -> UnifiedMemory:
    """
    Get singleton instance of unified memory"""
    if not hasattr(get_unified_memory, '_instance'):
        get_unified_memory._instance = UnifiedMemory()
    return get_unified_memory._instance

# Usage example for integration with existing orchestrator
if __name__ == "__main__":
    # Example usage
    memory = UnifiedMemory()
    
    # Store conversation
    memory.store_conversation_turn("user123", "user", "I want to build a web app")
    memory.store_conversation_turn("user123", "assistant", "I can help you build a web app. What features do you need?")
    
    # Store facts
    memory.store("Python is great for web development", MemoryType.FACT, 
                metadata={"key": "python_web_dev", "category": "programming"})
    
    # Store agent output
    memory.store_agent_output("PlannerAgent", "Generated 5-step plan for web app", "user123")
    
    # Query for context
    context = memory.get_conversation_context("user123", "What database should I use?")
    print(f"Context: {context['context_summary']}")
    
    # Get metrics
    metrics = memory.get_metrics()
    print(f"System metrics: {metrics}")