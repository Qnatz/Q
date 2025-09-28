# ideation_module.py
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from qllm.unified_llm import UnifiedLLM
from memory.prompt_manager import PromptManager
import logging

logger = logging.getLogger(__name__)

class IdeationStatus(Enum):
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class IdeationResult:
    status: IdeationStatus
    message: str
    project_title: Optional[str] = None
    refined_prompt: Optional[str] = None
    confirmation_message: Optional[str] = None

import random

class IdeationModule:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
        self._max_retries = 3

    def _get_ideation_prompt(self) -> str:
        """Get ideation prompt with dynamic opening line"""
        prompt = self.prompt_manager.get_prompt("ideation_prompt")
        if not prompt:
            self.logger.warning("Ideation prompt not found, using fallback")
            return self._get_fallback_ideation_prompt()

        return prompt

    def _get_fallback_ideation_prompt(self) -> str:
        """Fallback prompt when main prompt is unavailable"""
        return """You are a creative AI assistant helping users brainstorm software project ideas. 
        Your goal is to help refine vague ideas into concrete, buildable project specifications.
        
        Guidelines:
        - Ask clarifying questions to understand user needs
        - Suggest technical approaches and features
        - Help define project scope and requirements
        - When the idea is sufficiently refined, output a JSON object with project details
        
        Final output format when complete:
        {
            "status": "complete",
            "project_title": "Project Name",
            "refined_prompt": "Detailed project description",
            "confirmation_message": "Friendly confirmation message"
        }"""

    def _validate_ideation_response(self, response: str) -> Tuple[bool, Optional[Dict]]:
        """Validate and parse LLM response"""
        try:
            # The response should be a JSON object, and nothing else.
            parsed = json.loads(response)
            if isinstance(parsed, dict) and all(key in parsed for key in ["status", "project_title", "refined_prompt"]):
                return True, parsed
            return False, None
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.debug(f"JSON validation failed: {e}")
            return False, None

    def start_ideation_session(self, user_query: str) -> Dict[str, str]:
        """Start a new ideation session with improved error handling"""
        self.logger.info(f"Starting ideation session for query: {user_query}")
        
        # Use the LLM to generate an initial response based on the ideation prompt and user query
        system_prompt = self._get_ideation_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        initial_response = self.llm.generate(messages, use_tools=False)

        # Store the initial user query in history
        # This will be used in continue_ideation_session
        # For now, we just return the initial greeting
        return {"type": "ideation_turn", "message": initial_response}

    def continue_ideation_session(self, history: List[Dict]) -> Dict[str, str]:
        """Continue ideation session with conversation history"""
        self.logger.info(f"Continuing ideation session with {len(history)} messages")
        
        if not history:
            return {"type": "error", "message": "No conversation history provided"}

        for attempt in range(self._max_retries):
            try:
                system_prompt = self._get_ideation_prompt()
                messages = [{"role": "system", "content": system_prompt}] + history
                
                response_text = self.llm.generate(messages, use_tools=False)
                
                # Check for completion
                is_valid, parsed_response = self._validate_ideation_response(response_text.strip())
                if is_valid and parsed_response.get("status") == "complete":
                    self.logger.info("Ideation session completed successfully")
                    return {
                        "type": "ideation_complete",
                        "project_title": parsed_response["project_title"],
                        "refined_prompt": parsed_response["refined_prompt"],
                        "confirmation_message": parsed_response.get("confirmation_message", "Great! Let's build this!")
                    }
                else:
                    # If it's not a valid completion JSON, it's a conversational turn.
                    return {"type": "ideation_turn", "message": response_text.strip()}
                
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self._max_retries - 1:
                    return self._get_error_response("continue")

        return self._get_error_response("continue")

    def _get_error_response(self, context: str) -> Dict[str, str]:
        """Get appropriate error response based on context"""
        error_messages = {
            "start": "I had trouble starting our brainstorm. Could you please rephrase your idea?",
            "continue": "I seem to have lost my train of thought. Where were we in our brainstorming?"
        }
        return {"type": "error", "message": error_messages.get(context, "An error occurred during ideation.")}