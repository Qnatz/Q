import json
import logging
from memory.prompt_manager import PromptManager
from core.state_manager import ConversationState # Import ConversationState

logger = logging.getLogger(__name__)

class Router:
    def __init__(self, unified_llm, prompt_manager: PromptManager, context_builder):
        self.unified_llm = unified_llm
        self.prompt_manager = prompt_manager
        self.context_builder = context_builder

        self.routing_options_map = {
            "update_programmer": "- update_programmer: You should call this route if the user's message should be added to the programmer's currently running session.",
            "start_planner": "- start_planner: You should call this route if the user's message is a **well-defined, complete request** that can be immediately sent to the planner for execution. For example: \"create a simple web app that is a notepad\"",
            "update_planner": "- update_planner: You should call this route if the user sends a new message containing anything from a related request that the planner should plan for.",
            "resume_and_update_planner": "- resume_and_update_planner: You should call this route if the planner is currently interrupted, and the user's message includes additional context.",
            "create_new_issue": "- create_new_issue: Call this route if the user's request should create a new GitHub issue.",
            "start_planner_for_followup": "- start_planner_for_followup: You should call this route if the user's message is a followup request.",
            "no_op": "- no_op: This should be called when the user's message is not a new request, additional context, or a new issue to create.",
            "ideation": "- ideation: You should call this route if the user is **brainstorming initial, vague ideas** for a new project or software and needs help refining their thoughts into a concrete plan.",
            "code_assist": "- code_assist: You should call this route if the user is asking for help with code, refactoring, translation, interactive assistance, requirements clarification, or project enhancement.",
            "chat": "- chat: You should call this route for simple conversations, greetings like 'hello qai', casual chat, or when the user just wants to talk without a specific technical request.",
            "technical_inquiry": "- technical_inquiry: You should call this route if the user has specific technical questions that need research or detailed explanations."
        }

    def _get_available_routes(self, planner_status: str, programmer_status: str) -> str:
        available_routes = ["no_op", "chat", "technical_inquiry"]

        if planner_status == 'idle' and programmer_status == 'idle':
            available_routes.extend([
                "start_planner", "start_planner_for_followup",
                "create_new_issue", "ideation", "code_assist"
            ])

        if planner_status == 'running':
            available_routes.append("update_planner")

        if planner_status == 'interrupted':
            available_routes.append("resume_and_update_planner")

        if programmer_status == 'running':
            available_routes.append("update_programmer")

        # Return formatted string for prompt
        return "\n".join([self.routing_options_map.get(r, r) for r in available_routes])

    def get_route(self, user_query: str, state: dict, ignore_ideation_status: bool = False) -> (str, str):
        # Fallback-safe status fetch
        planner_status = state.get("module_status", {}).get("planner", "idle")
        programmer_status = state.get("module_status", {}).get("programmer", "idle")
        user_id = state.get("user_id", "default_user")
        request_source = state.get("request_source", "unknown")

        # Try to build context safely
        try:
            # Create a temporary state object if ignoring ideation status
            state_for_context = state
            if ignore_ideation_status:
                temp_state_dict = state.to_dict()
                temp_state_dict["is_in_ideation_session"] = False
                state_for_context = ConversationState(**temp_state_dict)

            context = self.context_builder.build_conversation_context(state_for_context)
            # context is a string here; also support dict fallbacks
            if isinstance(context, str):
                recent_conversation = context
                semantic_context = context
            else:
                recent_conversation = context.get("recent_conversation", "none")
                semantic_context = context.get("semantic_context", "none")
        except Exception as e:
            logger.warning(f"ContextBuilder failed, using defaults: {e}")
            recent_conversation = "none"
            semantic_context = "none"

        # Routing prompt
        routing_prompt = self.prompt_manager.get_prompt("manager_routing_prompt")
        if not routing_prompt:
            logger.error("Routing prompt not found.")
            return "error", "Routing prompt is missing."

        # Compute available routes
        available_routes = self._get_available_routes(planner_status, programmer_status)

        # Fill the routing prompt with safe defaults
        try:
            formatted_prompt = routing_prompt.format(
                PLANNER_STATUS=planner_status,
                PROGRAMMER_STATUS=programmer_status,
                conversation_history=recent_conversation,
                semantic_context=semantic_context,
                REQUEST_SOURCE=request_source,
                ROUTING_OPTIONS=available_routes if available_routes else "none"
            )
        except KeyError as e:
            logger.error(f"Routing prompt missing placeholder: {e}")
            formatted_prompt = routing_prompt  # fallback without formatting

        # Build messages for LLM
        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": f"{recent_conversation}\n\nUser Query: {user_query}"}
        ]

        # Call the LLM and parse response safely
        try:
            llm_response = self.unified_llm.generate(messages, use_tools=False)
            try:
                response_json = json.loads(llm_response)
                route = response_json.get("route")
                message = response_json.get("message")
                if route and message:
                    return route, message
                else:
                    return "no_op", "I could not determine a valid route. Please rephrase."
            except json.JSONDecodeError:
                return "no_op", "Received invalid JSON from LLM."
        except Exception as e:
            logger.error(f"Unexpected error during routing: {e}")
            return "no_op", "An unexpected error occurred during routing."
