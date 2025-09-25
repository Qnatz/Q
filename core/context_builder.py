# context_builder.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import json
import time
import httpx

from core.config import MAX_RECENT_TURNS, MAX_SUMMARY_TOKENS
from utils.ui_helpers import say_error
from core.state_manager import ConversationState

@dataclass
class SummaryCache:
    """Cache for conversation summaries to avoid redundant LLM calls"""
    message_hash: str
    summary: str
    timestamp: float

class ContextBuilder:
    def __init__(self, unified_llm, cache_size: int = 100):
        self.unified_llm = unified_llm
        self.cache_size = cache_size
        self._summary_cache: Dict[str, SummaryCache] = {}
        
    def _get_messages_hash(self, messages: List[dict]) -> str:
        """Generate hash for messages to use as cache key"""
        content_string = "|".join(
            f"{msg.get('role','')}:{msg.get('content','')}" 
            for msg in messages
        )
        return hashlib.md5(content_string.encode()).hexdigest()

    def summarize_old_history(self, old_messages: List[dict], max_summary_tokens: int = MAX_SUMMARY_TOKENS) -> str:
        """Generate concise summary with caching"""
        if not old_messages:
            return ""

        # Check cache first
        messages_hash = self._get_messages_hash(old_messages)
        if messages_hash in self._summary_cache:
            return self._summary_cache[messages_hash].summary

        try:
            combined_content = "\n".join(
                msg.get("content", "") for msg in old_messages 
                if msg.get("content")
            )
            
            system_prompt = {
                "role": "system",
                "content": (
                    "You are a concise summarizer. Summarize the conversation focusing on: "
                    "- User's main requirements and goals\n"
                    "- Key decisions made\n"
                    "- Outstanding questions or missing information\n"
                    "Keep it factual and under {max_tokens} tokens."
                ).format(max_tokens=max_summary_tokens)
            }
            
            user_prompt = {
                "role": "user", 
                "content": f"Conversation to summarize:\n\n{combined_content}\n\nProvide a concise summary:"
            }
            
            response = self.unified_llm.generate([system_prompt, user_prompt], use_tools=False)
            summary_text = self._extract_summary_text(response)
            
            # Cache the result
            self._update_cache(messages_hash, summary_text)
            
            return summary_text.strip()
            
        except Exception as e:
            say_error(f"History summarization failed: {e}")
            return self._create_fallback_summary(old_messages)

    def _extract_summary_text(self, response) -> str:
        """Extract summary text from various response formats"""
        if isinstance(response, dict):
            return response.get("content") or response.get("text") or ""
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def _create_fallback_summary(self, old_messages: List[dict]) -> str:
        """Create a fallback summary when LLM fails"""
        key_messages = old_messages[:3] + old_messages[-2:]  # First 3 and last 2 messages
        return " | ".join(
            msg.get("content", "")[:100].replace("\n", " ") 
            for msg in key_messages if msg.get("content")
        )

    def _update_cache(self, key: str, summary: str):
        """Update cache with LRU eviction policy"""
        if len(self._summary_cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = min(self._summary_cache.keys(), 
                           key=lambda k: self._summary_cache[k].timestamp)
            del self._summary_cache[oldest_key]
        
        self._summary_cache[key] = SummaryCache(
            message_hash=key,
            summary=summary,
            timestamp=time.time()
        )

    def get_ide_context(self) -> Dict[str, Any]:
        """Fetch IDE context from the local sidecar server."""
        try:
            response = httpx.get("http://127.0.0.1:8001/context", timeout=0.5)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except httpx.RequestError as e:
            # logger.warning(f"Could not connect to IDE server: {e}")
            return {"error": f"Could not connect to IDE server: {e}"}
        except json.JSONDecodeError:
            # logger.warning("IDE server returned invalid JSON.")
            return {"error": "IDE server returned invalid JSON."}
        except Exception as e:
            # logger.error(f"An unexpected error occurred while fetching IDE context: {e}")
            return {"error": f"An unexpected error occurred: {e}"}

    def build_conversation_context(self, state: dict) -> str:
        """Build optimized conversation context"""
        recent_messages = state["history"][-MAX_RECENT_TURNS:]
        recent_context = "\n".join(
            f"{msg['role']}: {msg['content']}" 
            for msg in recent_messages
        )
        
        # Handle older messages with summary
        if len(state["history"]) > MAX_RECENT_TURNS:
            old_messages = state["history"][:-MAX_RECENT_TURNS]
            summary = state.get("history_summary") or self.summarize_old_history(old_messages)
            state["history_summary"] = summary
            
            return (
                f"Previous context summary: {summary}\n\n"
                f"Recent conversation:\n{recent_context}"
            )
        
        return recent_context
