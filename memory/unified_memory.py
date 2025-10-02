import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict
import logging # Import logging

logger = logging.getLogger(__name__) # Get logger instance

# --- Memory Types ---
class MemoryType(Enum):
    CONVERSATION = "conversation"
    FACT = "fact"
    SEMANTIC = "semantic"

# --- Memory Entry ---
@dataclass
class MemoryEntry:
    id: str
    content: str
    type: MemoryType
    metadata: Dict[str, Any]
    timestamp: datetime
    user_id: str
    project_id: Optional[str] = None
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'type': self.type.value
        }

# --- TinyDB Manager ---
from tinydb import TinyDB, Query

class TinyDBManager:
    def __init__(self, db_path: str):
        self.db = TinyDB(db_path)
        self.history_table = self.db.table("history")
        self.facts_table = self.db.table("facts")
        self.projects_table = self.db.table("projects")
        self.state_table = self.db.table("state") # New table for state
        self.files_table = self.db.table("project_files")
        self.tasks_table = self.db.table("project_tasks")

    def store_conversation(self, user_id: str, role: str, content: str,
                           project_id: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
        entry_id = f"conv_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        entry = {
            "id": entry_id,
            "user_id": user_id,
            "project_id": project_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.history_table.insert(entry)
        return entry_id

    def get_conversation_history(self, user_id: str, project_id: Optional[str] = None):
        User = Query()
        query = (User.user_id == user_id)
        if project_id:
            query = query & (User.project_id == project_id)
        results = self.history_table.search(query)
        sorted_results = sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)
        return [{"content": r["content"], "metadata": r, "source": "tinydb"} for r in sorted_results]

    def store_fact(self, key: str, value: Any, category: str = "general",
                   user_id: str = "system", project_id: Optional[str] = None) -> str:
        fact_id = f"fact_{hashlib.md5(key.encode()).hexdigest()[:8]}"
        fact = {
            "id": fact_id,
            "key": key,
            "value": value,
            "category": category,
            "user_id": user_id,
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        Fact = Query()
        if self.facts_table.search((Fact.key == key) & (Fact.project_id == project_id)):
            self.facts_table.update(fact, (Fact.key == key) & (Fact.project_id == project_id))
        else:
            self.facts_table.insert(fact)
        return fact_id

    def search_facts(self, keyword: str, project_id: Optional[str] = None, limit: int = 5):
        Fact = Query()
        query = Fact.value.test(lambda v: keyword.lower() in str(v).lower())
        if project_id:
            query = query & (Fact.project_id == project_id)
        results = self.facts_table.search(query)
        return results[:limit]

    def store_project_metadata(self, project_id: str, metadata: Dict[str, Any]):
        Project = Query()
        if self.projects_table.search(Project.project_id == project_id):
            self.projects_table.update(metadata, Project.project_id == project_id)
        else:
            self.projects_table.insert(metadata)

    def get_project_metadata(self, project_id: str) -> Optional[Dict[str, Any]]:
        Project = Query()
        result = self.projects_table.search(Project.project_id == project_id)
        return result[0] if result else None

    def get_all_project_metadata(self, user_id: str) -> List[Dict[str, Any]]:
        Project = Query()
        results = self.projects_table.search(Project.user_id == user_id)
        return results

    def store_project_file(self, project_id: str, file_path: str, file_content: str):
        File = Query()
        entry = {"project_id": project_id, "path": file_path, "content": file_content}
        if self.files_table.search((File.project_id == project_id) & (File.path == file_path)):
            self.files_table.update(entry, (File.project_id == project_id) & (File.path == file_path))
        else:
            self.files_table.insert(entry)

    def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        File = Query()
        return self.files_table.search(File.project_id == project_id)

    def store_project_task(self, project_id: str, task_id: str, task_data: Dict[str, Any]):
        Task = Query()
        entry = {"project_id": project_id, "task_id": task_id, **task_data}
        if self.tasks_table.search((Task.project_id == project_id) & (Task.task_id == task_id)):
            self.tasks_table.update(entry, (Task.project_id == project_id) & (Task.task_id == task_id))
        else:
            self.tasks_table.insert(entry)

    def get_project_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        Task = Query()
        return self.tasks_table.search(Task.project_id == project_id)

    def store_state(self, key: str, value: Any, user_id: str = "system") -> str:
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
        return state_id

    def get_state(self, key: str, user_id: str = "system") -> Optional[Any]:
        State = Query()
        result = self.state_table.search((State.key == key) & (State.user_id == user_id))
        return result[0]["value"] if result else None

    def delete_state(self, key: str, user_id: str = "system"):
        State = Query()
        self.state_table.remove((State.key == key) & (State.user_id == user_id))

# --- ChromaDB Manager ---
class ChromaDBManager:
    def __init__(self, collection):
        self.collection = collection

    def store_embedding(self, memory_entry: MemoryEntry):
        self.collection.add(
            documents=[memory_entry.content],
        metadatas=[{k: v for k, v in {**memory_entry.metadata, "user_id": memory_entry.user_id, "project_id": memory_entry.project_id}.items() if v is not None}],
            ids=[memory_entry.id],
            embeddings=[memory_entry.embedding] if memory_entry.embedding else None
        )

    def similarity_search(self, query_text: str, top_k: int = 5, filters: Optional[Dict] = None):
        filters = filters or {}
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=filters
        )
        formatted = []
        for r_content, r_meta, r_id in zip(results['documents'][0], results['metadatas'][0], results['ids'][0]):
            formatted.append({"content": r_content, "metadata": r_meta, "id": r_id, "source": "chroma"})
        return formatted

    def get_all_semantic_memories(self):
        results = self.collection.get(include=['metadatas'])
        formatted = []
        for r_id, r_meta in zip(results['ids'], results['metadatas']):
            formatted.append({"id": r_id, "metadata": r_meta, "source": "chroma"})
        return formatted

# --- Unified Memory with Cache and Pruning ---
class UnifiedMemory:
    def __init__(self, tinydb_manager: TinyDBManager, chromadb_manager: ChromaDBManager,
                 max_cache_size: int = 50, prune_days: int = 90):
        self.tinydb = tinydb_manager
        self.chromadb = chromadb_manager
        self.max_cache_size = max_cache_size
        self.prune_days = prune_days
        self.project_cache = defaultdict(list)  # {project_id: [MemoryEntry,...]}
        logger.debug(f"UnifiedMemory initialized with id: {id(self)}")

    # --- Generic Memory Store ---
    def store(self, content: str, mem_type: MemoryType, user_id: str, metadata: Optional[Dict] = None,
              project_id: Optional[str] = None, embedding: Optional[List[float]] = None) -> str:
        entry_id = f"{mem_type.value}_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            type=mem_type,
            metadata=metadata or {},
            timestamp=datetime.now(),
            user_id=user_id,
            project_id=project_id,
            embedding=embedding
        )

        # Store in backend
        if mem_type == MemoryType.CONVERSATION:
            self.tinydb.store_conversation(user_id, metadata.get("role", "assistant"), content, project_id, metadata)
        elif mem_type == MemoryType.FACT:
            self.tinydb.store_fact(metadata.get("key", entry_id), content, metadata.get("category", "general"), user_id, project_id)
        elif mem_type == MemoryType.SEMANTIC:
            self.chromadb.store_embedding(entry)

        # Update project cache
        self.project_cache[project_id].append(entry)
        self._prune_cache(project_id)
        return entry_id

    # --- Conversation Methods ---
    def store_conversation_turn(self, user_id: str, role: str, content: str,
                                project_id: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
        enhanced_metadata = {"role": role, "turn_type": "conversation", **(metadata or {})}
        return self.store(content, MemoryType.CONVERSATION, user_id, enhanced_metadata, project_id)

    def get_conversation_context(self, user_id: str, current_query: str,
                                 project_id: Optional[str] = None,
                                 context_turns: int = 5, semantic_results: int = 3) -> Dict[str, Any]:
        recent_history = self.tinydb.get_conversation_history(user_id, project_id)
        semantic_context = self.chromadb.similarity_search(
            current_query,
            semantic_results,
            filters={"user_id": user_id, "project_id": project_id} if project_id else {"user_id": user_id}
        )
        fact_context = self.tinydb.search_facts(current_query, project_id)[:2]

        # Include cached memory if available
        cached_entries = [e.to_dict() for e in self.project_cache.get(project_id, []) if current_query.lower() in e.content.lower()]

        context_summary = self._generate_context_summary(recent_history, semantic_context, fact_context, cached_entries)

        return {
            "recent_conversation": recent_history,
            "semantic_context": semantic_context,
            "relevant_facts": fact_context,
            "cached_context": cached_entries,
            "context_summary": context_summary
        }

    def _generate_context_summary(self, conversation, semantic, facts, cached):
        summary = " ".join([c["content"] for c in conversation])
        summary += " " + " ".join([s["content"] for s in semantic])
        summary += " " + " ".join([f["value"] for f in facts])
        summary += " " + " ".join([c["content"] for c in cached])
        return summary.strip()

    # --- Cache Pruning ---
    def _prune_cache(self, project_id: Optional[str]):
        if project_id not in self.project_cache:
            return
        # Remove oldest if over max size
        if len(self.project_cache[project_id]) > self.max_cache_size:
            self.project_cache[project_id] = self.project_cache[project_id][-self.max_cache_size:]
        # Remove entries older than prune_days
        cutoff = datetime.now() - timedelta(days=self.prune_days)
        self.project_cache[project_id] = [e for e in self.project_cache[project_id] if e.timestamp >= cutoff]

    def store_project_metadata(self, project_id: str, metadata: Dict[str, Any]):
        self.tinydb.store_project_metadata(project_id, metadata)

    def get_project_metadata(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self.tinydb.get_project_metadata(project_id)

    def get_all_project_metadata(self, user_id: str) -> List[Dict[str, Any]]:
        return self.tinydb.get_all_project_metadata(user_id)

    def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        return self.tinydb.get_project_files(project_id)

    def get_project_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        return self.tinydb.get_project_tasks(project_id)

    def store_prompt(self, name: str, content: str, metadata: Optional[Dict] = None) -> str:
        enhanced_metadata = {
            "prompt_name": name,
            **(metadata or {})
        }
        return self.store(content, MemoryType.SEMANTIC, user_id="system", metadata=enhanced_metadata)

    def get_prompt(self, name: str) -> Optional[str]:
        # Directly query chromadb for prompts by name
        results = self.chromadb.collection.get(
            where={
                "prompt_name": name
            },
            include=['documents']
        )
        if results and results['documents']:
            return results['documents'][0]
        return None

    def get_all_prompts(self) -> Dict[str, Any]:
        all_semantic_memories = self.chromadb.get_all_semantic_memories()
        prompt_ids = []
        for mem in all_semantic_memories:
            if mem['metadata'] and "prompt_name" in mem['metadata']:
                prompt_ids.append(mem['metadata']["prompt_name"])
        return {"ids": prompt_ids}
