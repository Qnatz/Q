import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.config import ResponseType, MAX_TURNS_BEFORE_BUILD
from utils.ui_helpers import say_assistant, say_error, say_system
from core.state_manager import ConversationState
from schemas.project_schema import ProjectMetadata
import logging
import os

logger = logging.getLogger(__name__)


class ResponseHandler:
    def __init__(
        self,
        unified_llm,
        state_manager,
        context_builder,
        workflow_manager,
        researcher,
        ideator,
        router,
        agent_manager,
        code_assist
    ):
        self.unified_llm = unified_llm
        self.state_manager = state_manager
        self.context_builder = context_builder
        self.workflow_manager = workflow_manager
        self.researcher = researcher
        self.ideator = ideator
        self.router = router
        self.agent_manager = agent_manager
        self.code_assist = code_assist

    def _continue_ideation_workflow(self, user_query: str, state: ConversationState) -> dict:
        """Continues an ongoing ideation session."""
        ideation_start_index = state.ideation_session_start_index
        full_history = state.history
        ideation_history = [msg for msg in full_history[ideation_start_index:] if msg.get("role") in ("user", "assistant")]
        
        response = self.ideator.continue_ideation_session(ideation_history)

        if response.get("type") == "ideation_complete":
            say_assistant(response["confirmation_message"])
            
            project_name = response["project_title"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_id = f"{project_name.replace(' ', '_').lower()}-{timestamp}"
            
            project_metadata = ProjectMetadata(
                project_id=project_id,
                project_name=project_name,
                refined_prompt=response["refined_prompt"],
                user_id=state.user_id,
                status="ideation_complete",
                completion_rate=0.1,
                conversation_history=state.history
            )
            self.state_manager.unified_memory.store_project_metadata(
                project_metadata.project_id, 
                project_metadata.to_dict()
            )
            
            state.current_project_id = project_id
            state.pending_build_confirmation = {
                "type": ResponseType.BUILD.value,
                "refined_prompt": response["refined_prompt"],
                "project_title": project_name,
                "project_id": project_id
            }
            state.is_in_ideation_session = False
            
            return {
                "type": "ideation_complete",
                "message": response["confirmation_message"]
            }
        else:
            say_assistant(response.get("message", "I'm not sure how to proceed with ideation."))
            return {
                "type": "ideation",
                "message": response.get("message", "I'm not sure how to proceed with ideation.")
            }

    def handle_response(self, response: dict, user_id: str, project_id: Optional[str] = None):
        """Handle response with streamlined routing system"""
        route = response.get("type")
        message = response.get("message", "I'm not sure how to proceed.")
        state = self.state_manager.get_conversation_state(user_id, project_id)

        # Handle ongoing ideation session
        if state.is_in_ideation_session:
            history = state.history
            if history:
                last_message = history[-1]
                content = (
                    last_message.get("content")
                    if isinstance(last_message, dict)
                    else getattr(last_message, "content", "")
                )
                return self._continue_ideation_workflow(content, state)
            return {"type": "error", "message": "No history in ideation session"}

        # Extract user query from history
        history = state.history
        if history:
            last_message = history[-1]
            user_query = (
                last_message.get("content")
                if isinstance(last_message, dict)
                else getattr(last_message, "content", "")
            )
        else:
            user_query = ""

        # Route handling
        if route == "start_planner":
            self.initiate_build_workflow(user_query, state)
            
        elif route == "update_programmer":
            self._handle_update_programmer(user_query, state)
            
        elif route == "update_planner":
            self._handle_update_planner(user_query, state)
            
        elif route == "resume_and_update_planner":
            self._handle_resume_and_update_planner(user_query, state)
            
        elif route == "create_new_issue":
            self._handle_create_new_issue(user_query, state)
            
        elif route == "start_planner_for_followup":
            self._handle_start_planner_for_followup(user_query, state)
            
        elif route == "code_assist":
            return self._handle_code_assist(user_query, state)
            
        elif route == "chat":
            return self._handle_chat(user_query, state)
            
        elif route == "technical_inquiry":
            return self._handle_technical_inquiry_workflow(user_query, state)
            
        elif route == "no_op":
            self._handle_no_op(user_query, state)
            
        elif route == "ideation":
            state.is_in_ideation_session = True
            state.ideation_session_start_index = len(state.history) - 1
            return self._continue_ideation_workflow(user_query, state)
            
        else:
            say_assistant(message)
            return {"type": route, "message": message}

    def _handle_chat(self, user_query: str, state: ConversationState) -> dict:
        """Handle simple chat conversations like greetings"""
        system_message_content = """You are QAI, a super-intelligent and enthusiastic AI Solution Architect. Your main goal is to inspire the user and collaboratively build amazing software.

Your chat persona:
- Always be encouraging, friendly, and slightly informal.
- Always steer the conversation towards building a new project.
- If the user just wants to chat or is looking for ideas, you MUST take the initiative. Use the `web_search` tool to find exciting, recent news in AI, software development, or technology. 
- Summarize the most interesting finding and present it to the user as a potential project idea."""

        # Build context using the context_builder
        try:
            context_string = self.context_builder.build_conversation_context(state)
        except Exception as e:
            logger.warning(f"Failed to build context for chat: {e}")
            context_string = ""

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": f"{context_string}\n\nUser Query: {user_query}"}
        ]

        try:
            raw_response = self.unified_llm.generate(messages, use_tools=True)
            
            say_assistant(raw_response.strip())
            return {
                "type": ResponseType.CHAT.value,
                "message": raw_response.strip(),
            }

        except Exception as e:
            say_error(f"Error generating response: {e}")
            fallback_msg = "I'm here to help! What would you like to build today?"
            say_assistant(fallback_msg)
            return {
                "type": ResponseType.CHAT.value,
                "message": fallback_msg
            }

    def initiate_build_workflow(self, refined_prompt: str, state):
        """Initiate build workflow with refined prompt"""
        pending_build = getattr(state, 'pending_build_confirmation', None) or {}
        
        project_title = pending_build.get("project_title")
        if not project_title:
            # If no project title, create a generic one from the prompt
            project_title = "Project" # Or generate from refined_prompt
        
        project_id = pending_build.get("project_id")
        if not project_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_id = f"{project_title.replace(' ', '_').lower()}-{timestamp}"
            state.current_project_id = project_id

            # Store metadata for new project
            project_metadata = ProjectMetadata(
                project_id=project_id,
                project_name=project_title,
                refined_prompt=refined_prompt,
                user_id=state.user_id,
                status="ideation_complete",
                completion_rate=0.1,
                conversation_history=state.history
            )
            self.state_manager.unified_memory.store_project_metadata(
                project_metadata.project_id, 
                project_metadata.to_dict()
            )

        response_dict = {
            "type": "build",
            "refined_prompt": refined_prompt,
            "project_title": project_title,
            "project_id": project_id
        }
        self.workflow_manager.execute_workflow(response_dict)

    def _handle_update_programmer(self, user_query: str, state):
        logger.info(f"Handling programmer update: {user_query}")
        return {"type": "update_programmer", "message": "Programmer update handling"}

    def _handle_update_planner(self, user_query: str, state):
        logger.info(f"Handling planner update: {user_query}")
        return {"type": "update_planner", "message": "Planner update handling"}

    def _handle_resume_and_update_planner(self, user_query: str, state):
        logger.info(f"Resuming and updating planner: {user_query}")
        return {"type": "resume_and_update_planner", "message": "Resume planner handling"}

    def _handle_create_new_issue(self, user_query: str, state):
        logger.info(f"Creating new issue: {user_query}")
        return {"type": "create_new_issue", "message": "Create issue handling"}

    def _handle_start_planner_for_followup(self, user_query: str, state):
        logger.info(f"Starting planner for followup: {user_query}")
        return {"type": "start_planner_for_followup", "message": "Followup planner handling"}

    def _handle_no_op(self, user_query: str, state):
        return {"type": "no_op", "message": "No operation needed"}

    def _handle_technical_inquiry_workflow(self, user_query: str, state):
        logger.info(f"Handling technical inquiry: {user_query}")
        # Use researcher module for technical questions
        try:
            response = self.researcher.research(user_query)
            say_assistant(response)
            return {"type": "technical_inquiry", "message": response}
        except Exception as e:
            logger.error(f"Error in technical inquiry: {e}")
            fallback = "I can help research that. Could you provide more details?"
            say_assistant(fallback)
            return {"type": "technical_inquiry", "message": fallback}

    def _handle_code_assist(
        self,
        user_query: str,
        state: ConversationState
    ) -> dict:
        """Handle code assistance, requirements clarification, and enhancement"""
        say_system("Initiating code assistance and requirement analysis.")

        system_message = {
            "role": "system",
            "content": """You are a technical assistant specializing in:
1. Code help, refactoring, debugging, and translation
2. Requirements clarification and extraction
3. Project enhancement and vision refinement
4. Technical consultation and guidance

When helping users:
- If they need code help, provide direct assistance with examples
- If requirements are unclear, ask specific clarifying questions (max 2)
- If a project idea needs enhancement, expand on their vision
- Always move toward actionable next steps"""
        }

        try:
            # Direct code help
            if any(
                kw in user_query.lower()
                for kw in [
                    "code", "function", "class", "bug",
                    "error", "refactor", "debug"
                ]
            ):
                response = self.code_assist.assist_code(user_query, state)
                say_assistant(
                    response.get("message", "I'm ready to help with your code.")
                )
                return response
            else:
                # Requirements clarification / enhancement
                try:
                    context_string = self.context_builder.build_conversation_context(state)
                except Exception as e:
                    logger.warning(f"Failed to build context: {e}")
                    context_string = ""
                    
                messages = [
                    system_message,
                    {
                        "role": "user",
                        "content": f"{context_string}\n\n{user_query}"
                    }
                ]
                llm_response = self.unified_llm.generate(
                    messages,
                    use_tools=False
                )
                say_assistant(llm_response.strip())
                return {
                    "type": ResponseType.CODE_ASSIST.value,
                    "message": llm_response.strip(),
                }
        except Exception as e:
            say_error(f"Error in code assistance: {e}")
            return {
                "type": ResponseType.CODE_ASSIST.value,
                "message": (
                    "I encountered an issue while assisting. "
                    "Could you please rephrase your request?"
                ),
            }
