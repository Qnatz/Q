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

    def _continue_ideation_workflow(self, user_query: str, state: ConversationState):
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
                completion_rate=0.1, # 10% complete after ideation
                conversation_history=state.history # Store full history for context
            )
            self.state_manager.unified_memory.store_project_metadata(project_metadata.project_id, project_metadata.to_dict()) # Pass project_id and metadata
            
            # Update ConversationState with the new project_id and pending build info
            state.current_project_id = project_id
            state.pending_build_confirmation = {
                "type": ResponseType.BUILD.value,
                "refined_prompt": response["refined_prompt"],
                "project_title": project_name, # Keep original project title for display
                "project_id": project_id # Pass the generated project_id
            }

            state.is_in_ideation_session = False
            # No return here, as handle_response will continue after this.
        else:
            # Display the message from the ideator's response
            say_assistant(response.get("message", "I'm not sure how to proceed with ideation."))



    def handle_response(self, response: dict, user_id: str, project_id: Optional[str] = None):
        """Handle response with streamlined routing system"""
        route = response.get("type")
        message = response.get("message", "I'm not sure how to proceed.")
        state = self.state_manager.get_conversation_state(user_id, project_id)

        if state.is_in_ideation_session:
            history = state.history
            if history:
                last_message = history[-1]
                content = (
                    last_message.get("content")
                    if isinstance(last_message, dict)
                    else getattr(last_message, "content", "")
                )
                self._continue_ideation_workflow(content, state)
            return

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

        # Streamlined route handling
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
            self._handle_code_assist(user_query, state)
        elif route == "no_op":
            self._handle_no_op(user_query, state)
        elif route == "ideation":
            state.is_in_ideation_session = True
            state.ideation_session_start_index = len(state.history)
            
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
                    completion_rate=0.1, # 10% complete after ideation
                    conversation_history=state.history # Store full history for context
                )
                self.state_manager.unified_memory.store_project_metadata(project_metadata.project_id, project_metadata.to_dict()) # Pass project_id and metadata
                
                # Update ConversationState with the new project_id and pending build info
                state.current_project_id = project_id
                state.pending_build_confirmation = {
                    "type": ResponseType.BUILD.value,
                    "refined_prompt": response["refined_prompt"],
                    "project_title": project_name, # Keep original project title for display
                    "project_id": project_id # Pass the generated project_id
                }

                state.is_in_ideation_session = False
                return {"type": "ideation_complete", "message": response["confirmation_message"]}
            else:
                # Display the message from the ideator's response
                say_assistant(response.get("message", "I'm not sure how to proceed with ideation."))
    def _handle_chat(self, user_query: str, state: ConversationState) -> dict:
        """Handle simple chat conversations like greetings"""
        system_message_content = """You are QAI, a super-intelligent and enthusiastic AI Solution Architect. Your main goal is to inspire the user and collaboratively build amazing software.

Your chat persona:
- Always be encouraging, friendly, and slightly informal.
- Always steer the conversation towards building a new project.
- If the user just wants to chat or is looking for ideas, you MUST take the initiative. Use the `web_search` tool to find exciting, recent news in AI, software development, or technology. 
- Summarize the most interesting finding and present it to the user as a potential project idea."""

        # Build context using the context_builder
        context_string = self.context_builder.build_conversation_context(state)

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": f"{context_string}\n\nUser Query: {user_query}"}
        ]

        try:
            raw_response = self.unified_llm.generate(messages, use_tools=True)
            
            return {
                "type": ResponseType.CHAT.value,
                "message": raw_response.strip(),
            }

        except Exception as e:
            say_error(f"Error generating response: {e}")
            return self._fallback_response(user_query, state)
        if route == "technical_inquiry":
            self._handle_technical_inquiry_workflow(user_query, state)
        else:
            say_assistant(message)

    # --- Skipping unchanged helper methods for brevity ---
    # (They stay exactly as in your file)

    def initiate_build_workflow(self, refined_prompt: str, state):
        """Initiate build workflow with refined prompt"""
        response_dict = {
            "type": "build",
            "refined_prompt": refined_prompt,
            "project_title": (getattr(state, 'pending_build_confirmation') or {}).get("project_title", "Project")
        }
        self.workflow_manager.execute_workflow(response_dict)

    def _handle_update_programmer(self, user_query: str, state):
        return {"type": "no_op", "message": "Programmer update handling"}

    def _handle_update_planner(self, user_query: str, state):
        return {"type": "no_op", "message": "Planner update handling"}

    def _handle_resume_and_update_planner(self, user_query: str, state):
        return {"type": "no_op", "message": "Resume planner handling"}

    def _handle_create_new_issue(self, user_query: str, state):
        return {"type": "no_op", "message": "Create issue handling"}

    def _handle_start_planner_for_followup(self, user_query: str, state):
        return {"type": "no_op", "message": "Followup planner handling"}

    def _handle_no_op(self, user_query: str, state):
        return {"type": "no_op", "message": "No operation needed"}

    def _handle_technical_inquiry_workflow(self, user_query: str, state):
        return {"type": "technical_inquiry", "message": "Technical inquiry handling"}

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
                context_string = self.context_builder.build_conversation_context(state)
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
