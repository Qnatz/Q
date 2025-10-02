from typing import Callable

class PlannerContextPackager:
    def __init__(self, memory: UnifiedMemory, max_summary_length: int = 2000):
        self.memory = memory
        self.max_summary_length = max_summary_length

    def package_context(self, user_id: str, current_query: str,
                        project_id: Optional[str] = None,
                        context_turns: int = 5,
                        semantic_results: int = 5,
                        relevance_fn: Optional[Callable[[str, str], float]] = None) -> Dict[str, Any]:
        """
        Packages context for planner usage.
        - relevance_fn: Optional function to score relevance between query and a memory entry.
        """
        context_data = self.memory.get_conversation_context(
            user_id,
            current_query,
            project_id,
            context_turns,
            semantic_results
        )

        # --- Flatten all entries ---
        all_entries = (
            [{"type": "conversation", "content": c["content"], "metadata": c.get("metadata", {})}
             for c in context_data["recent_conversation"]] +
            [{"type": "semantic", "content": s["content"], "metadata": s.get("metadata", {})}
             for s in context_data["semantic_context"]] +
            [{"type": "fact", "content": f["value"], "metadata": f} for f in context_data["relevant_facts"]] +
            [{"type": "cached", "content": c["content"], "metadata": c.get("metadata", {})}
             for c in context_data["cached_context"]]
        )

        # --- Rank by relevance if function provided ---
        if relevance_fn:
            all_entries.sort(key=lambda e: relevance_fn(current_query, e["content"]), reverse=True)

        # --- Build summary text, respecting max length ---
        summary_text = ""
        packaged_entries = []
        for entry in all_entries:
            entry_text = entry["content"].strip()
            if len(summary_text) + len(entry_text) + 1 > self.max_summary_length:
                break
            summary_text += entry_text + " "
            packaged_entries.append(entry)

        # --- Final structured payload ---
        payload = {
            "query": current_query,
            "project_id": project_id,
            "user_id": user_id,
            "summary_text": summary_text.strip(),
            "entries": packaged_entries,
            "total_entries": len(all_entries),
            "included_entries": len(packaged_entries),
        }

        return payload
