# orchestrator.py
import json
import logging
import sys
from datetime import datetime

from rich.console import Console
from rich.live import Live
from rich.status import Status

from core.agent_manager import AgentManager
from core.context_builder import ContextBuilder
from core.llm_service import LLMService
from core.response_handler import ResponseHandler
from core.router import Router
from core.state_manager import StateManager
from core.ui import say_assistant, say_error, say_system, say_user
from core.workflow_manager import WorkflowManager
from memory.prompt_manager import PromptManager
from core.ide_server import IDEServer

logger = logging.getLogger(__name__)
console = Console()


class OrchestratorAgent:
    def __init__(self):
        self.state_manager = StateManager()
        self.agent_manager = AgentManager()
        self.prompt_manager = PromptManager() # Corrected initialization
        self.llm_service = LLMService(self.agent_manager.unified_llm, self.prompt_manager)
        self.context_builder = ContextBuilder(self.llm_service)
        self.router = Router(self.agent_manager.unified_llm, self.agent_manager.prompt_manager) # Corrected initialization
        self.workflow_manager = WorkflowManager(
            self.agent_manager.planner,
            self.agent_manager.manager,
            self.agent_manager.programmer,
            self.agent_manager.qa,
            self.agent_manager.reviewer,
        )
        self.response_handler = ResponseHandler(
            self.agent_manager.unified_llm,
            self.state_manager,
            self.context_builder,
            self.workflow_manager,
            self.agent_manager.researcher,
            self.agent_manager.ideator,
            self.router,
            self.agent_manager,
        )
        # Initialize and start IDE server
        self.ide_server = IDEServer()
        self.ide_server.run_in_thread()

    def process_query(self, user_query: str, user_id: str) -> dict:
        """Process user query with proper state handling"""
        try:
            state = self.state_manager.get_conversation_state(user_id)

            state.history.append(
                {
                    "role": "user",
                    "content": user_query,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            state.turn += 1

            # Route the query
            route, message = self.router.get_route(user_query, state)
            response_dict = {"type": route, "message": message}

            # Handle the response
            self.response_handler.handle_response(response_dict, user_id)

            state.history.append(
                {
                    "role": "assistant",
                    "content": json.dumps(response_dict),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            self.state_manager._update_conversation_state(user_id, state)
            return response_dict

        except Exception as e:
            say_error(f"Error processing query: {e}")
            logger.exception("Detailed error in process_query")
            return {
                "type": "error",
                "message": "I encountered an error processing your request.",
            }

    def run(self):
        """Main execution loop"""



        user_id = "default_user"

        while True:
            try:
                user_input = console.input("[bold blue]💭 You > [/bold blue]").strip()

                if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                    say_system(
                        "👋 Thanks for brainstorming! Come back anytime with new ideas."
                    )
                    break

                if not user_input:
                    continue


                with Status("[bold green]Assistant is thinking...", console=console, spinner="dots"):
                    response = self.process_query(user_input, user_id)



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
