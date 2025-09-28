import json
from typing import List, Tuple

from memory.prompt_manager import PromptManager
from qllm.unified_llm import UnifiedLLM
from utils.ui_helpers import say_error


class LLMService:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager

    def summarize_old_history(
        self,
        old_messages: List[dict],
        max_summary_tokens: int,
    ) -> str:
        """Generate concise summary with caching"""
        if not old_messages:
            return ""

        try:
            combined_content = "\n".join(
                msg.get("content", "") for msg in old_messages if msg.get("content")
            )

            system_prompt = {
                "role": "system",
                "content": (
                    "You are a concise summarizer. Summarize the conversation focusing on: "
                    "- User's main requirements and goals\n"
                    "- Key decisions made\n"
                    "- Outstanding questions or missing information\n"
                    "Keep it factual and under {max_tokens} tokens."
                ).format(max_tokens=max_summary_tokens),
            }

            user_prompt = {
                "role": "user",
                "content": f"Conversation to summarize:\n\n{combined_content}\n\nProvide a concise summary:",
            }

            response = self.llm.generate(
                [system_prompt, user_prompt], use_tools=False
            )
            summary_text = self._extract_summary_text(response)

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
        key_messages = (
            old_messages[:3] + old_messages[-2:]
        )  # First 3 and last 2 messages
        return " | ".join(
            msg.get("content", "")[:100].replace("\n", " ")
            for msg in key_messages
            if msg.get("content")
        )

    def generate_code(self, prompt: str, system_message: str = "You are an expert Python programmer. Generate clean, efficient, and well-documented code.") -> str:
        """Generates code based on a given prompt."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]
        try:
            logging.debug(f"Raw prompt sent to LLM: {messages}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            return response.strip()
        except Exception as e:
            say_error(f"Code generation failed: {e}")
            return ""