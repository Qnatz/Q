# ideation_module.py
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from core.llm_service import LLMService
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
    turn_number: int = 0
    blueprint: Optional[Dict[str, str]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class IdeationModule:
    """
    Multi-turn ideation module that expands and refines project ideas.
    Uses progressive depth: Turn 1 (sketch) -> Turn 2 (outline) -> Turn 3 (blueprint)
    """
    
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager, 
                 max_turns: int = 3):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
        self._max_retries = 3
        self.max_turns = max_turns
        self.refinement_history: List[IdeationResult] = []
        self.current_turn = 0

    def _get_ideation_prompt(self, turn_number: int = 0) -> str:
        """Get ideation prompt with turn-specific depth guidance"""
        base_prompt = self.prompt_manager.get_prompt("ideation_prompt")
        if not base_prompt:
            self.logger.warning("Ideation prompt not found, using fallback")
            base_prompt = self._get_fallback_ideation_prompt()
        
        # Add turn context
        turn_context = self._get_turn_context(turn_number)
        return f"{base_prompt}\n\n{turn_context}"

    def _get_turn_context(self, turn_number: int) -> str:
        """Provide context about current turn depth"""
        contexts = {
            0: "TURN 1: Generate explosive initial ideas with multiple possibilities and specific technical proposals.",
            1: "TURN 2: Architect the chosen direction across all dimensions with detailed technical stack and feature design.",
            2: "TURN 3: Crystallize into production-ready blueprint with implementation clarity and final details."
        }
        return contexts.get(turn_number, contexts[2])

    def _get_fallback_ideation_prompt(self) -> str:
        """Fallback prompt when main prompt is unavailable"""
        return """You are QAI, an AI solution architect who GENERATES and EXPANDS software project ideas.
        
        You don't interview—you IDEATE. Take vague ideas and explode them into rich, multi-dimensional projects.
        
        Your approach:
        - Generate multiple concrete possibilities with specific technologies
        - Propose bold features and capabilities they haven't mentioned
        - Make architectural decisions with clear reasoning
        - Paint vivid pictures of user experiences
        - Think across dimensions: technical, UX, business, risks, timeline
        
        Be specific: Use actual technology names (PostgreSQL not "a database")
        Be creative: Imagine possibilities beyond what they said
        Be decisive: Make recommendations, don't just ask questions
        
        Final output format when they say "build", "go ahead", "let's do it":
        {
            "status": "complete",
            "project_title": "ProjectName",
            "refined_prompt": "Comprehensive project description with specific technical details",
            "confirmation_message": "Enthusiastic confirmation message",
            "blueprint": {
                "problem": "Specific problem definition",
                "solution": "Detailed solution with innovations",
                "technology": "Complete stack with justifications",
                "business": "Value proposition",
                "users": "User ecosystem",
                "risks": "Key risks and mitigation",
                "roadmap": "Phased implementation plan"
            }
        }"""

    def _validate_ideation_response(self, response: str) -> Tuple[bool, Optional[Dict]]:
        self.logger.info(f"Validating response: {response}")
        """Validate and parse LLM response for completion JSON"""
        # Quick check: must look like JSON
        stripped = response.strip()
        if not (stripped.startswith('{') and stripped.endswith('}')):
            return False, None

        try:
            parsed = json.loads(stripped)
            required_keys = ["status", "project_title", "refined_prompt"]
            if isinstance(parsed, dict) and all(key in parsed for key in required_keys):
                return True, parsed
            return False, None
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.debug(f"JSON validation failed: {e}")
            return False, None

    def _detect_build_signal(self, message: str) -> bool:
        """Detect if user wants to proceed to building"""
        build_signals = [
            "build", "create", "start project", "go ahead", "let's build",
            "proceed", "let's do it", "make it", "i'm ready", "sounds good let's go"
        ]
        message_lower = message.lower()
        return any(signal in message_lower for signal in build_signals)

    def _extract_project_details_from_history(self, history: List[Dict]) -> Tuple[str, str, Dict]:
        """Extract project title, refined prompt, and blueprint from conversation history"""
        project_title = "SoftwareProject"
        refined_prompt = ""
        blueprint = {}
        
        # Try to find JSON in previous assistant messages
        for msg in reversed(history):
            if msg["role"] == "assistant":
                # Check for JSON response
                if msg["content"].strip().startswith('{'):
                    try:
                        parsed = json.loads(msg["content"])
                        if parsed.get("project_title"):
                            project_title = parsed["project_title"]
                        if parsed.get("refined_prompt"):
                            refined_prompt = parsed["refined_prompt"]
                        if parsed.get("blueprint"):
                            blueprint = parsed["blueprint"]
                        break
                    except json.JSONDecodeError:
                        pass
                
                # Use last substantive message as refined prompt
                if not refined_prompt and len(msg["content"]) > 100:
                    content = msg["content"]
                    try:
                        # content might be a JSON string from the orchestrator
                        parsed_content = json.loads(content)
                        if isinstance(parsed_content, dict) and "message" in parsed_content:
                            content = parsed_content["message"]
                    except (json.JSONDecodeError, TypeError):
                        pass
                    refined_prompt = content
        
        # Generate title from initial query if still generic
        if project_title == "SoftwareProject" and len(history) > 0:
            initial_query = history[0]["content"]
            # Take first few meaningful words
            words = [w for w in initial_query.split() if len(w) > 2][:3]
            if words:
                project_title = "".join(w.capitalize() for w in words)
        
        # If no refined prompt found, synthesize from conversation
        if not refined_prompt:
            refined_prompt = self._synthesize_refined_prompt(history)
        
        return project_title, refined_prompt, blueprint

    def _synthesize_refined_prompt(self, history: List[Dict]) -> str:
        """Synthesize a refined prompt from conversation history using LLM"""
        # Get last few substantive exchanges
        recent_messages = history[-6:] if len(history) > 6 else history
        
        synthesis_request = """Based on this conversation, create a comprehensive project description (200+ words) that includes:
        - What problem is being solved
        - The proposed solution and key features
        - Technology stack and architecture
        - Target users
        - Implementation approach
        
        Write as a detailed project specification, not a conversation summary."""
        
        try:
            messages = recent_messages + [{"role": "user", "content": synthesis_request}]
            synthesized = self.llm_service.llm.generate(messages, use_tools=False)
            return synthesized.strip()
        except Exception as e:
            self.logger.error(f"Failed to synthesize refined prompt: {e}")
            # Fallback: concatenate assistant messages
            return " ".join([
                msg["content"] for msg in history 
                if msg["role"] == "assistant"
            ])

    def start_ideation_session(self, user_query: str) -> Dict[str, str]:
        """Start a new ideation session"""
        self.logger.info(f"Starting ideation session: {user_query[:50]}...")
        self.current_turn = 0
        self.refinement_history = []
        
        system_prompt = self._get_ideation_prompt(turn_number=0)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        try:
            response = self.llm_service.llm.generate(messages, use_tools=False)
            
            result = IdeationResult(
                status=IdeationStatus.ACTIVE,
                message=response,
                turn_number=0
            )
            self.refinement_history.append(result)
            
            return {
                "type": "ideation_turn",
                "message": response,
                "turn": 0,
                "max_turns": self.max_turns
            }
        except Exception as e:
            self.logger.error(f"Failed to start ideation: {e}")
            return self._get_error_response("start")

    def continue_ideation_session(self, history: List[Dict]) -> Dict[str, str]:
        """Continue ideation with conversation history"""
        self.logger.info(f"Continuing ideation session with {len(history)} messages")
        
        if not history:
            return {"type": "error", "message": "No conversation history provided"}

        # Calculate current turn (count user messages)
        self.current_turn = sum(1 for m in history if m["role"] == "user") - 1
        
        last_user_message = history[-1]["content"] if history[-1]["role"] == "user" else ""

        for attempt in range(self._max_retries):
            try:
                # Check for build signal
                if self._detect_build_signal(last_user_message):
                    self.logger.info("Build signal detected, finalizing ideation")
                    return self._finalize_ideation(history)

                # Check if max turns reached
                if self.current_turn >= self.max_turns:
                    self.logger.info("Max turns reached, suggesting finalization")
                    return self._suggest_finalization(history)

                # Continue ideation with appropriate depth
                system_prompt = self._get_ideation_prompt(turn_number=self.current_turn)
                messages = [{"role": "system", "content": system_prompt}] + history
                
                response = self.llm_service.llm.generate(messages, use_tools=False)
                
                # Check if LLM initiated completion
                is_valid, parsed_response = self._validate_ideation_response(response)
                if is_valid and parsed_response.get("status") == "complete":
                    self.logger.info("LLM-initiated completion detected")
                    return self._create_completion_response(parsed_response)
                
                # Regular ideation turn
                result = IdeationResult(
                    status=IdeationStatus.ACTIVE,
                    message=response,
                    turn_number=self.current_turn
                )
                self.refinement_history.append(result)
                
                # Add progress indicator
                progress_note = ""
                if self.current_turn < self.max_turns - 1:
                    progress_note = f"\n\n💡 Refinement turn {self.current_turn + 1}/{self.max_turns}. Continue refining or type 'build' when ready."
                elif self.current_turn == self.max_turns - 1:
                    progress_note = "\n\n✨ Final refinement turn! When you're ready, type 'build' to create the project."
                
                return {
                    "type": "ideation_turn",
                    "message": response + progress_note,
                    "turn": self.current_turn,
                    "max_turns": self.max_turns
                }
                
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self._max_retries - 1:
                    return self._get_error_response("continue")

        return self._get_error_response("continue")

    def _suggest_finalization(self, history: List[Dict]) -> Dict[str, str]:
        """Suggest moving to build phase after max turns"""
        project_title, refined_prompt, blueprint = self._extract_project_details_from_history(history)
        
        suggestion = (
            f"We've refined this idea through {self.max_turns} turns and have a solid foundation! "
            f"I think we're ready to build **{project_title}**. Type 'build' to proceed to implementation, "
            f"or continue refining if you'd like to explore more."
        )
        
        return {
            "type": "ideation_turn",
            "message": suggestion,
            "turn": self.current_turn,
            "max_turns": self.max_turns,
            "suggestion": "finalize"
        }

    def _finalize_ideation(self, history: List[Dict]) -> Dict[str, str]:
        """Finalize ideation and prepare for builder"""
        self.logger.info("Finalizing ideation session")
        
        project_title, refined_prompt, blueprint = self._extract_project_details_from_history(history)
        
        # If blueprint is empty, create basic one
        if not blueprint:
            blueprint = {
                "problem": "Problem addressed by this project",
                "solution": "Solution approach and key features",
                "technology": "Technology stack and architecture",
                "business": "Value proposition and model",
                "users": "Target users and stakeholders",
                "risks": "Key risks and mitigation strategies",
                "roadmap": "Implementation phases and timeline"
            }
        
        confirmation = (
            f"🚀 Excellent! Let's build **{project_title}**. "
            f"I've synthesized our {self.current_turn + 1} refinement turns into a comprehensive project specification. "
            f"Ready to start implementation!"
        )
        
        return {
            "type": "ideation_complete",
            "project_title": project_title,
            "refined_prompt": refined_prompt,
            "confirmation_message": confirmation,
            "blueprint": blueprint,
            "refinement_turns": self.current_turn + 1
        }

    def _create_completion_response(self, parsed_response: Dict) -> Dict[str, str]:
        """Create completion response from LLM-generated JSON"""
        return {
            "type": "ideation_complete",
            "project_title": parsed_response["project_title"],
            "refined_prompt": parsed_response["refined_prompt"],
            "confirmation_message": parsed_response.get(
                "confirmation_message", 
                f"Great! Let's build {parsed_response['project_title']}!"
            ),
            "blueprint": parsed_response.get("blueprint", {}),
            "refinement_turns": self.current_turn + 1
        }

    def _get_error_response(self, context: str) -> Dict[str, str]:
        """Get appropriate error response"""
        error_messages = {
            "start": "I had trouble starting our ideation. Could you rephrase your idea?",
            "continue": "I seem to have lost track. Could you clarify where we are in the ideation?"
        }
        return {
            "type": "error", 
            "message": error_messages.get(context, "An error occurred during ideation.")
        }
    
    def get_refinement_summary(self) -> Dict:
        """Get summary of refinement progress"""
        return {
            "total_turns": len(self.refinement_history),
            "current_turn": self.current_turn,
            "max_turns": self.max_turns,
            "completed": self.current_turn >= self.max_turns,
            "history": [
                {
                    "turn": r.turn_number,
                    "status": r.status.value,
                    "timestamp": r.timestamp,
                    "message_length": len(r.message)
                }
                for r in self.refinement_history
            ]
        }
