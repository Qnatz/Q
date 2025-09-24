import json
import re
from datetime import datetime
from typing import Optional, Dict, Any

from core.config import ResponseType, MAX_TURNS_BEFORE_BUILD
from utils.ui_helpers import say_assistant, say_error, say_system
from core.state_manager import ConversationState
import logging

logger = logging.getLogger(__name__)

class ResponseHandler:
    def __init__(self, unified_llm, state_manager, context_builder, workflow_manager, researcher, ideator, router, agent_manager):
        self.unified_llm = unified_llm
        self.state_manager = state_manager
        self.context_builder = context_builder
        self.workflow_manager = workflow_manager
        self.researcher = researcher
        self.ideator = ideator
        self.router = router
        self.agent_manager = agent_manager

    def _safe_state_access(self, state, key: str, default: Any = None) -> Any:
        """Safely access state attributes with fallback support"""
        try:
            if hasattr(state, '__getitem__'):
                return state[key]
            elif hasattr(state, key):
                return getattr(state, key)
            elif hasattr(state, 'get'):
                return state.get(key, default)
            else:
                return default
        except (KeyError, AttributeError, TypeError) as e:
            return default

    def _safe_state_update(self, state, key: str, value: Any):
        """Safely update state attributes with fallback support"""
        try:
            if hasattr(state, '__setitem__'):
                state[key] = value
            elif hasattr(state, key) or hasattr(state, '__setattr__'):
                setattr(state, key, value)
            else:
                logger.warning(f"Cannot update state key: {key}")
        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to update state key {key}: {e}")

    def handle_response(self, response: dict, user_id: str):
        """Handle response with proper state access"""
        route = response.get("type")
        message = response.get("message", "I'm not sure how to proceed.")
        
        state = self.state_manager.get_conversation_state(user_id)

        if self._safe_state_access(state, "is_in_ideation_session", False):
            history = self._safe_state_access(state, "history", [])
            if history:
                last_message = history[-1]
                content = last_message.get("content") if isinstance(last_message, dict) else getattr(last_message, "content", "")
                self._continue_ideation_workflow(content, state)
            return
        elif self._safe_state_access(state, "is_in_correction_session", False):
            history = self._safe_state_access(state, "history", [])
            if history:
                last_message = history[-1]
                content = last_message.get("content") if isinstance(last_message, dict) else getattr(last_message, "content", "")
                self._continue_correction_workflow(content, state)
            return

        history = self._safe_state_access(state, "history", [])
        if history:
            last_message = history[-1]
            user_query = last_message.get("content") if isinstance(last_message, dict) else getattr(last_message, "content", "")
        else:
            user_query = ""

        if route == "start_planner":
            self._initiate_build_workflow(user_query, state)
        elif route == "update_programmer":
            self._handle_update_programmer(user_query, state)
        elif route == "code_correction":
            self._handle_code_correction(user_query, state)
        elif route == "ideation":
            self._handle_ideation(user_query, state)
        elif route == "chat":
            self._generate_intelligent_response(user_query, json.dumps(history), state)
        elif route == "technical_inquiry":
            self._handle_technical_inquiry_workflow(user_query, state)
        elif route == "enhance":
            self._handle_enhance_workflow(user_query, state)
        elif route == "extract":
            self._handle_extract_workflow(user_query, state)
        elif route == "resume_and_update_planner":
            self._handle_resume_and_update_planner(user_query, state)
        elif route == "create_new_issue":
            self._handle_create_new_issue(user_query, state)
        elif route == "start_planner_for_followup":
            self._handle_start_planner_for_followup(user_query, state)
        else:
            say_assistant(message)

    def _initiate_build_workflow(self, user_query: str, state: dict):
        say_system("Initiating build workflow.")
        project_title = " ".join(user_query.split()[:5])
        response_dict = {
            "project_title": project_title,
            "refined_prompt": user_query
        }
        plan_json_str = self.workflow_manager.execute_workflow(response_dict)
        try:
            plan_data = json.loads(plan_json_str)
            say_assistant(f"Here is the plan I've come up with:\n\n{json.dumps(plan_data, indent=2)}")
        except json.JSONDecodeError:
            say_error(f"Failed to parse plan: {plan_json_str}")
            say_assistant("I've generated a plan, but I had trouble displaying it. Please check the logs for details.")

    def _handle_update_programmer(self, user_query: str, state: ConversationState):
        say_error("Updating the programmer is not yet implemented.")

    def _handle_code_correction(self, user_query: str, state: ConversationState) -> dict:
        say_system("Initiating code correction workflow.")
        self._safe_state_update(state, "is_in_correction_session", True)
        
        correction_state = {
            "phase": "awaiting_description",
            "user_request": user_query,
            "investigation_summary": "",
            "proposed_plan": "",
            "verification_command": ""
        }
        self._safe_state_update(state, "code_correction_state", correction_state)

        return {
            "type": ResponseType.CODE_CORRECTION.value,
            "message": "I understand you'd like me to fix or refactor some code. To start, please describe the bug or the changes you'd like me to make in more detail.",
        }

    def _continue_correction_workflow(self, user_query: str, state: ConversationState) -> dict:
        correction_state = self._safe_state_access(state, "code_correction_state", {})
        phase = correction_state.get("phase") if isinstance(correction_state, dict) else ""

        if phase == "awaiting_description":
            say_system(f"User has described the issue: {user_query}. Beginning investigation.")
            self._safe_state_update(correction_state, "phase", "investigation")
            self._safe_state_update(state, "code_correction_state", correction_state)

            tool_registry = self.agent_manager.tool_registry
            search_results = tool_registry.execute_tool("search_file_content", {"pattern": user_query})
            
            if search_results.status != "success" or not search_results.result:
                return {"type": ResponseType.CODE_CORRECTION.value, "message": "I couldn't find any relevant files based on your description. Could you be more specific?"}

            file_paths = [result['file_path'] for result in search_results.result]
            unique_file_paths = list(set(file_paths))
            file_contents_result = tool_registry.execute_tool("read_many_files", {"paths": unique_file_paths})

            if file_contents_result.status != "success" or not file_contents_result.result:
                return {"type": ResponseType.CODE_CORRECTION.value, "message": "I found some relevant files, but I had trouble reading them."}
            file_contents = file_contents_result.result

            analysis_prompt = f"""The user wants to fix a bug. Their request is: '{user_query}'.

I have found the following relevant file contents:
{file_contents}

Based on this information, please provide a concise analysis and a specific plan to fix the issue.
Your response must be a JSON object with two keys: 'investigation_summary' and 'proposed_plan'.
'investigation_summary': A short, one-sentence summary of the root cause.
'proposed_plan': A clear, one-sentence description of the exact change you will make, including the file and line number if possible."""
            
            llm_response = self.unified_llm.generate([{"role": "system", "content": "You are an expert software engineer specializing in debugging."}, {"role": "user", "content": analysis_prompt}])
            
            try:
                plan_data = json.loads(llm_response)
                summary = plan_data['investigation_summary']
                plan = plan_data['proposed_plan']
            except (json.JSONDecodeError, KeyError):
                return {"type": ResponseType.CODE_CORRECTION.value, "message": "I analyzed the code but had trouble forming a clear plan. Could you provide more context?"}

            self._safe_state_update(correction_state, "investigation_summary", summary)
            self._safe_state_update(correction_state, "proposed_plan", plan)
            self._safe_state_update(correction_state, "phase", "awaiting_confirmation")
            self._safe_state_update(state, "code_correction_state", correction_state)

            return {
                "type": ResponseType.CODE_CORRECTION.value,
                "message": f"I have investigated the codebase. Here is my analysis:\n\n**Summary:** {summary}\n**Proposed Plan:** {plan}\n\nShould I proceed with this fix?",
            }
        
        elif phase == "awaiting_confirmation":
            positive_responses = ["yes", "ok", "proceed", "looks good", "y", "correct"]
            if user_query.lower().strip() in positive_responses:
                say_system("User has approved the plan. Implementing the fix.")
                self._safe_state_update(correction_state, "phase", "implementing")

                tool_registry = self.agent_manager.tool_registry
                proposed_plan = self._safe_state_access(correction_state, "proposed_plan", "")
                
                implementation_prompt = f"""Based on the following plan, what is the exact call to the `robust_replace` tool to fix the code? 
                Plan: {proposed_plan}
                Your output MUST be a single, valid JSON object for the tool call, like:
                {{"tool_name": "robust_replace", "parameters": {{"file_path": "...", "old_string": "...", "new_string": "..."}}}} """

                llm_response = self.unified_llm.generate([{"role": "system", "content": "You are an expert at using tools."}, {"role": "user", "content": implementation_prompt}])
                
                try:
                    tool_call = json.loads(llm_response)
                    fix_result = tool_registry.execute_tool(tool_call["tool_name"], tool_call["parameters"])
                except (json.JSONDecodeError, KeyError):
                    return {"type": ResponseType.CODE_CORRECTION.value, "message": "I had trouble understanding how to apply the fix. Let's try again."}

                if fix_result.status != "success":
                    return {"type": ResponseType.CODE_CORRECTION.value, "message": f"I tried to apply the fix, but something went wrong: {fix_result.error_message}"}

                self._safe_state_update(correction_state, "phase", "verifying")
                self._safe_state_update(state, "code_correction_state", correction_state)
                return {
                    "type": ResponseType.CODE_CORRECTION.value,
                    "message": "The fix has been applied. Is there a command I can run to verify that the fix was successful (e.g., a test command)?",
                }
            else:
                say_system("User has rejected the plan. Returning to awaiting_description.")
                self._safe_state_update(correction_state, "phase", "awaiting_description")
                self._safe_state_update(state, "code_correction_state", correction_state)
                return {
                    "type": ResponseType.CODE_CORRECTION.value,
                    "message": "Okay, I will not apply that fix. Could you please describe the issue again with more detail or suggest a different approach?",
                }

        elif phase == "verifying":
            no_responses = ["no", "none", "skip"]
            if user_query.lower().strip() in no_responses:
                say_system("User chose not to verify. Ending session.")
                self._safe_state_update(state, "is_in_correction_session", False)
                return {
                    "type": ResponseType.CODE_CORRECTION.value,
                    "message": "Okay, the code correction process is complete.",
                }
            else:
                say_system(f"User provided verification command: {user_query}")
                tool_registry = self.agent_manager.tool_registry
                verification_result = tool_registry.execute_tool("run_shell_command", {"command": user_query})

                self._safe_state_update(state, "is_in_correction_session", False)

                if verification_result.status == "success" and self._safe_state_access(verification_result.result, "exit_code") == 0:
                    return {
                        "type": ResponseType.CODE_CORRECTION.value,
                        "message": f"I ran the command `{user_query}` and it completed successfully. The fix is verified!",
                    }
                else:
                    return {
                        "type": ResponseType.CODE_CORRECTION.value,
                        "message": f"I ran the command `{user_query}` but it seems to have failed. You may need to investigate further.\n\nStdout:\n{self._safe_state_access(verification_result.result, 'stdout')}\nStderr:\n{self._safe_state_access(verification_result.result, 'stderr')}",
                    }

        return {
            "type": ResponseType.CODE_CORRECTION.value,
            "message": "I'm in the middle of a code correction. Please tell me how to proceed.",
        }

    def _handle_ideation(self, user_query: str, state: ConversationState) -> dict:
        say_assistant("That's a great starting point! Let's brainstorm and refine this idea together.")
        self._safe_state_update(state, "is_in_ideation_session", True)
        
        history = self._safe_state_access(state, "history", [])
        ideation_history = [msg for msg in history if self._safe_state_access(msg, "role") in ("user", "assistant")]
        
        response = self.ideator.continue_ideation_session(ideation_history)
        return response

    def _continue_ideation_workflow(self, user_query: str, state: dict) -> dict:
        ideation_history = [msg for msg in self._safe_state_access(state, "history", []) if self._safe_state_access(msg, "role") in ("user", "assistant")]
        
        response = self.ideator.continue_ideation_session(ideation_history)

        if response.get("type") == "ideation_complete":
            say_assistant(response["confirmation_message"])
            self._safe_state_update(state, "pending_build_confirmation", {
                "type": ResponseType.BUILD.value,
                "refined_prompt": response["refined_prompt"],
                "project_title": response["project_title"]
            })
            self._safe_state_update(state, "is_in_ideation_session", False)
            return {"type": "ideation_complete", "message": response["confirmation_message"]}
        else:
            # Display the message from the ideator's response
            say_assistant(response.get("message", "I'm not sure how to proceed with ideation."))

        return response

    def _generate_intelligent_response(self, query: str, conversation: str, state: ConversationState) -> dict:
        system_message = {
            "role": "system",
            "content": """You are QAI, a super-intelligent and enthusiastic AI Solution Architect. Your main goal is to inspire the user and collaboratively build amazing software.

Your chat persona:
- Always be encouraging, friendly, and slightly informal.
- Always steer the conversation towards building a new project.
- If the user just wants to chat or is looking for ideas, you MUST take the initiative. Use the `web_search` tool to find exciting, recent news in AI, software development, or technology. 
- Summarize the most interesting finding and present it to the user as a potential project idea."""
        }

        user_message = {"role": "user", "content": query}

        history = self._safe_state_access(state, "history", [])
        messages = [system_message] + history + [user_message]

        try:
            raw_response = self.unified_llm.generate(messages, use_tools=True)
            
            return {
                "type": ResponseType.CHAT.value,
                "message": raw_response.strip(),
            }

        except Exception as e:
            say_error(f"Error generating response: {e}")
            return self._fallback_response(query, state)

    def _fallback_response(self, query: str, state: ConversationState) -> dict:
        if any(word in query.lower() for word in ['hello', 'hi', 'hey']):
            message = "Hello! I'm here to help you turn your ideas into working software. What would you like to build?"
        else:
            message = "That's interesting! Tell me more about what you're trying to accomplish. What problem would this solve?"
            
        return {
            "type": ResponseType.EXTRACT.value,
            "message": message,
        }

    def _handle_technical_inquiry_workflow(self, user_query: str, state: ConversationState) -> dict:
        say_assistant("Researching your question now...")
        research_task = {"query": user_query}
        research_result = self.researcher.execute(research_task)
        
        system_message = {
            "role": "system",
            "content": "You are a helpful technical assistant. Your task is to provide clear explanations, code examples, or comparisons based on the user's technical inquiry."
        }
        user_message = {"role": "user", "content": f"User Inquiry: {user_query}\nResearch Result: {research_result}"}
        
        try:
            llm_response = self.unified_llm.generate([system_message, user_message], use_tools=False)
            
            return {
                "type": ResponseType.TECHNICAL_INQUIRY.value,
                "message": llm_response.strip(),
            }
        except Exception as e:
            say_error(f"LLM generation for technical inquiry failed: {e}")
            return {
                "type": ResponseType.TECHNICAL_INQUIRY.value,
                "message": "I encountered an issue while generating the explanation. Please try rephrasing your question.",
            }

    def _handle_enhance_workflow(self, user_query: str, state: ConversationState):
        say_error("Enhance workflow is not yet implemented.")

    def _handle_extract_workflow(self, user_query: str, state: ConversationState):
        say_error("Extract workflow is not yet implemented.")

    def _handle_resume_and_update_planner(self, user_query: str, state: ConversationState):
        say_error("Resume and update planner is not yet implemented.")

    def _handle_create_new_issue(self, user_query: str, state: dict):
        say_error("Create new issue is not yet implemented.")

    def _handle_start_planner_for_followup(self, user_query: str, state: dict):
        say_error("Start planner for followup is not yet implemented.")

    def _clean_message_format(self, message: str) -> str:
        if isinstance(message, dict):
            message = json.dumps(message)
        if "```json" in message or "{" in message:
            lines = message.split('\n')
            clean_lines = []
            in_json = False
            
            for line in lines:
                if "```json" in line or line.strip().startswith('{'):
                    in_json = True
                    continue
                elif "```" in line or line.strip().endswith('}'):
                    in_json = False
                    continue
                elif not in_json and line.strip() and not line.strip().startswith('"'):
                    clean_lines.append(line)
            
            if clean_lines:
                return '\n'.join(clean_lines).strip()
            else:
                return "Let me help you build this project!"
        
        return message.strip()

    def _handle_code_execution(self, response: dict, user_id: str):
        state = self.state_manager.get_conversation_state(user_id)
        user_query = self._safe_state_access(state, "history", [])[-1].get("content")
        
        say_system("🔧 Direct code execution started...")
        
        say_assistant("I'm analyzing your code and will implement the necessary fixes.")
