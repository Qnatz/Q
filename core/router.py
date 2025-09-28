import json
import re
import logging
from memory.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class Router:
    def __init__(self, unified_llm, prompt_manager: PromptManager):
        self.unified_llm = unified_llm
        self.prompt_manager = prompt_manager
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
        """
        Determines the available routing options based on the status of the modules.
        """
        available_routes = ["no_op", "chat", "technical_inquiry"]

        if planner_status == 'idle' and programmer_status == 'idle':
            available_routes.extend(["start_planner", "start_planner_for_followup", "create_new_issue", "ideation", "code_assist"])
        
        if planner_status == 'running':
            available_routes.append("update_planner")
        
        if planner_status == 'interrupted':
            available_routes.append("resume_and_update_planner")

        if programmer_status == 'running':
            available_routes.append("update_programmer")

        return "\n".join([self.routing_options_map[route] for route in available_routes])

    def get_route(self, user_query: str, state: dict) -> (str, str):
        """
        Determines the route for a user query based on the conversation state.
        """
        planner_status = state.get("module_status", {}).get("planner", "idle")
        programmer_status = state.get("module_status", {}).get("programmer", "idle")
        history = state.get("history", [])

        prompt = self.prompt_manager.get_prompt("manager_routing_prompt")
        if not prompt:
            logger.error("Error: Could not load the routing prompt.")
            return "no_op", "I encountered an internal error. Please try again."

        available_routes_str = self._get_available_routes(planner_status, programmer_status)
        
        # Dynamically create the placeholder values for the prompt
        prompt_placeholders = {key: "" for key in self.routing_options_map.keys()}
        for route in self.routing_options_map.keys():
            if route in available_routes_str:
                prompt_placeholders[route] = self.routing_options_map[route]

        task_plan_prompt = self.prompt_manager.get_prompt("TASK_PLAN_PROMPT") or ""
        proposed_plan_prompt = self.prompt_manager.get_prompt("PROPOSED_PLAN_PROMPT") or ""
        conversation_history_prompt = self.prompt_manager.get_prompt("CONVERSATION_HISTORY_PROMPT") or ""

        formatted_prompt = prompt.format(
            PLANNER_STATUS=planner_status,
            PROGRAMMER_STATUS=programmer_status,
            CONVERSATION_HISTORY=json.dumps(history, indent=2),
            ROUTING_OPTIONS=available_routes_str,
            TASK_PLAN_PROMPT=task_plan_prompt,
            PROPOSED_PLAN_PROMPT=proposed_plan_prompt,
            CONVERSATION_HISTORY_PROMPT=conversation_history_prompt,
            REQUEST_SOURCE="user_input" # Placeholder for now
        )

        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": user_query}
        ]

        try:
            llm_response = self.unified_llm.generate(messages, use_tools=False)
            try:
                # The response is a JSON string, so we parse it directly
                response_json = json.loads(llm_response)
                route = response_json.get("route")
                message = response_json.get("message")

                if route and message:
                    return route, message
                else:
                    logger.error("LLM response did not contain a valid route or message.")
                    return "no_op", "I had trouble deciding what to do next. Could you please rephrase?"
            except json.JSONDecodeError:
                logger.error("LLM returned an invalid JSON response.")
                return "no_op", "I received an invalid response. Could you please try again?"
        except Exception as e:
            logger.error(f"An unexpected error occurred during routing: {e}")
            return "no_op", "An unexpected error occurred during routing."
