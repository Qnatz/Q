# orchestrator.py
import json
import sys
from datetime import datetime
from typing import Optional, Any

from rich.console import Console

from core.config import ResponseType
from core.state_manager import StateManager, ConversationState
from core.agent_manager import AgentManager, AgentConfig
from core.context_builder import ContextBuilder
from core.router import Router
from core.response_handler import ResponseHandler
from core.workflow_manager import WorkflowManager
from core.ui import say_assistant, say_user, say_system, say_error
import logging

logger = logging.getLogger(__name__)
console = Console()

class OrchestratorAgent:
    def __init__(self, llm_mode: str = None, llama_endpoint: str = None):
        self.state_manager = StateManager()
        agent_config_args = {}
        if llm_mode is not None:
            agent_config_args['llm_mode'] = llm_mode
        if llama_endpoint is not None:
            agent_config_args['llama_endpoint'] = llama_endpoint
        config = AgentConfig(**agent_config_args)
        self.agent_manager = AgentManager(config)
        self.context_builder = ContextBuilder(self.agent_manager.unified_llm)
        self.router = Router(self.agent_manager.unified_llm, self.agent_manager.prompt_manager)
        self.workflow_manager = WorkflowManager(
            self.agent_manager.planner,
            self.agent_manager.manager,
            self.agent_manager.programmer,
            self.agent_manager.qa,
            self.agent_manager.reviewer
        )
        self.response_handler = ResponseHandler(
            self.agent_manager.unified_llm,
            self.state_manager,
            self.context_builder,
            self.workflow_manager,
            self.agent_manager.researcher,
            self.agent_manager.ideator,
            self.router,
            self.agent_manager
        )

    def _safe_state_access(self, state: ConversationState, key: str, default: Any = None) -> Any:
        """Safely access state attributes with fallback"""
        try:
            # Try dictionary-style access first (for backward compatibility)
            if hasattr(state, '__getitem__'):
                return state[key]
            # Then try attribute access
            elif hasattr(state, key):
                return getattr(state, key)
            else:
                return default
        except (KeyError, AttributeError, TypeError) as e:
            logger.debug(f"Safe state access failed for key '{key}': {e}")
            return default

    def process_query(self, user_query: str, user_id: str) -> dict:
        """Process user query with proper state handling"""
        try:
            state = self.state_manager.get_conversation_state(user_id)
            
            # Add user message to history using proper state access
            if hasattr(state, 'history'):
                state.history.append({
                    "role": "user", 
                    "content": user_query, 
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                # Fallback for dictionary-style state
                state["history"].append({
                    "role": "user", 
                    "content": user_query, 
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Update turn count
            if hasattr(state, 'turn'):
                state.turn += 1
            else:
                state["turn"] = state.get("turn", 0) + 1

            # Route the query
            route, message = self.router.get_route(user_query, state)
            response_dict = {"type": route, "message": message}

            # Handle the response
            self.response_handler.handle_response(response_dict, user_id)

            # Add assistant response to history
            if hasattr(state, 'history'):
                state.history.append({
                    "role": "assistant", 
                    "content": json.dumps(response_dict),
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                state["history"].append({
                    "role": "assistant", 
                    "content": json.dumps(response_dict),
                    "timestamp": datetime.utcnow().isoformat()
                })

            self.state_manager._update_conversation_state(user_id, state)
            return response_dict

        except Exception as e:
            say_error(f"Error processing query: {e}")
            logger.exception("Detailed error in process_query")
            return {"type": "error", "message": "I encountered an error processing your request."}

    def run(self):
        """Main execution loop"""
        welcome_message = (
            "🎯 **AI Solution Architect**\n\n"
            "I transform your ideas into working software! Just tell me:\n"
            "• What problem you're trying to solve\n"
            "• What you wish existed\n"
            "• Any workflow you want to automate\n\n"
            "I'll handle all the technical details. What's on your mind?"
        )
        
        say_assistant(welcome_message)
        user_id = "default_user"

        while True:
            try:
                user_input = console.input("[bold blue]💭 You > [/bold blue]").strip()
                
                if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                    say_system("👋 Thanks for brainstorming! Come back anytime with new ideas.")
                    break
                    
                if not user_input:
                    continue

                say_user(user_input)
                response = self.process_query(user_input, user_id)
                
                # Display the message from the response_dict
                if response and response.get("message"):
                    say_assistant(response["message"])

            except KeyboardInterrupt:
                say_system("\n👋 Session ended. Your ideas are always welcome!")
                break
            except Exception as e:
                say_error(f"Unexpected error: {e}")
                logger.exception("Unexpected error in main loop")
                continue

if __name__ == "__main__":
    try:
        orchestrator = OrchestratorAgent()
        
        if len(sys.argv) > 1:
            initial_query = " ".join(sys.argv[1:])
            say_user(initial_query)
            orchestrator.process_query(initial_query, "default_user")
        else:
            orchestrator.run()
            
    except Exception as e:
        say_error(f"Failed to start orchestrator: {e}")
        sys.exit(1)