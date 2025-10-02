# orchestrator.py
import json
import logging
logger = logging.getLogger(__name__)
import sys
from datetime import datetime
from typing import Optional

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

# Import UnifiedMemory and its dependencies
from memory.unified_memory import UnifiedMemory, TinyDBManager, ChromaDBManager
import chromadb
from chromadb.config import Settings

console = Console()


class OrchestratorAgent:
    def __init__(self):
        # Instantiate UnifiedMemory and its dependencies
        tinydb_manager = TinyDBManager(db_path="data/storage/tinydb.json") # Changed path
        
        chroma_client = chromadb.PersistentClient(
            path="data/storage/chromadb",
            settings=Settings(anonymized_telemetry=False)
        )
        chroma_collection = chroma_client.get_or_create_collection(
            name="prompts",
            metadata={"description": "QAI Agent prompt storage"}
        )
        chromadb_manager = ChromaDBManager(collection=chroma_collection)
        
        unified_memory = UnifiedMemory(tinydb_manager=tinydb_manager, chromadb_manager=chromadb_manager)

        self.state_manager = StateManager(unified_memory=unified_memory)
        self.agent_manager = AgentManager(unified_memory=unified_memory, state_manager=self.state_manager) # Pass unified_memory and state_manager
        self.prompt_manager = PromptManager(unified_memory=unified_memory) # Pass unified_memory
        self.llm_service = LLMService(self.agent_manager.unified_llm, self.prompt_manager)
        self.context_builder = ContextBuilder(self.agent_manager.unified_llm, self.state_manager.unified_memory)
        self.router = Router(self.agent_manager.unified_llm, self.agent_manager.prompt_manager, self.context_builder)
        self.workflow_manager = WorkflowManager(
            self.agent_manager.planner,
            self.agent_manager.manager,
            self.agent_manager.programmer,
            self.agent_manager.qa,
            self.agent_manager.reviewer,
            self.state_manager,
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
            self.agent_manager.code_assist,
        )
        # Initialize and start IDE server
        self.ide_server = IDEServer()
        self.ide_server.run_in_thread()

    def _display_and_select_project(self, user_id: str) -> Optional[str]:
        projects = self.state_manager.unified_memory.get_all_project_metadata(user_id)
        if not projects:
            say_system("No existing projects found. Let's start a new one!")
            return None

        say_system("Existing Projects:")
        for i, project in enumerate(projects):
            say_system(f"{i + 1}. {project['project_name']} (Status: {project['status']}, Completion: {project['completion_rate']:.0%})")

        while True:
            choice = console.input("[bold blue]💭 Enter the number of the project to resume, or type 'new' to start a new project: [/bold blue]").strip()
            if choice.lower() == 'new':
                return None
            try:
                index = int(choice) - 1
                if 0 <= index < len(projects):
                    return projects[index].project_id
                else:
                    say_error("Invalid project number. Please try again.")
            except ValueError:
                say_error("Invalid input. Please enter a number or 'new'.")

    def process_query(self, user_query: str, user_id: str) -> dict:
        """Process user query with proper state handling"""
        try:
            # First, get the user's general state to find the current project ID
            general_state = self.state_manager.get_conversation_state(user_id)
            project_id = general_state.current_project_id

            # Now, get the project-specific state
            state = self.state_manager.get_conversation_state(user_id, project_id)

            state.history.append(
                {
                    "role": "user",
                    "content": user_query,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            state.turn += 1

            # Determine the intended route without considering current ideation session status
            # This helps in breaking out of a lingering ideation session if a new, clear request is made.
            potential_route, _ = self.router.get_route(user_query, state, ignore_ideation_status=True)

            # If a new, non-ideation route is detected, clear the ideation session flag
            if state.is_in_ideation_session and potential_route not in ["ideation", "no_op", "chat", "technical_inquiry"]:
                logger.info(f"Breaking out of ideation session due to new request: {potential_route}")
                state.is_in_ideation_session = False

            # Route the query or continue ideation/resumed workflow
            if state.is_in_ideation_session:
                route = "ideation"
                message = user_query # Pass the user query directly to the ideation handler
            elif state.current_project_id and state.current_phase != "conversation":
                # If a project is resumed, route based on its current phase
                route = state.current_phase
                message = user_query # Pass the user query, might be a command to continue
            else:
                route, message = self.router.get_route(user_query, state)
            response_dict = {"type": route, "message": message}

            # Handle the response
            self.response_handler.handle_response(response_dict, user_id, project_id)

            # Check if ideation is complete and a build is pending
            if state.pending_build_confirmation:
                refined_prompt = state.pending_build_confirmation.get("refined_prompt")
                project_title = state.pending_build_confirmation.get("project_title")
                if refined_prompt and project_title:
                    self.response_handler.initiate_build_workflow(refined_prompt, state)
                    response_dict = {"type": "build_initiated", "message": f"Initiating build for {project_title}."}
                else:
                    response_dict = {"type": "error", "message": "Ideation complete, but missing refined prompt or project title for build."}
                state.pending_build_confirmation = None # Clear the pending build confirmation

            state.history.append(
                {
                    "role": "assistant",
                    "content": json.dumps(response_dict),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            self.state_manager._update_conversation_state(user_id, state, project_id)
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

        # Display existing projects and allow selection
        selected_project_id = self._display_and_select_project(user_id)

        if selected_project_id:
            say_system(f"Resuming project: {selected_project_id}")
            # Load the project state and set it as current
            project_metadata = self.state_manager.unified_memory.get_project_metadata(selected_project_id)
            if project_metadata:
                # Reconstruct conversation state from project metadata
                state = self.state_manager.get_conversation_state(user_id, selected_project_id)
                state.history = project_metadata.conversation_history
                state.current_project_id = project_metadata.project_id
                state.pending_build_confirmation = {
                    "type": "build",
                    "refined_prompt": project_metadata.refined_prompt,
                    "project_title": project_metadata.project_name,
                    "project_id": project_metadata.project_id
                }
                # Set the current phase based on project status for resumption
                if project_metadata.status == "ideation_complete":
                    state.current_phase = "planning"
                elif project_metadata.status == "planning_complete":
                    state.current_phase = "programming"
                elif project_metadata.status == "programming":
                    state.current_phase = "qa"
                elif project_metadata.status == "qa":
                    state.current_phase = "review"
                elif project_metadata.status == "review":
                    state.current_phase = "completed"
                
                self.state_manager._update_conversation_state(user_id, state, selected_project_id)
                say_system(f"Project {project_metadata.project_name} loaded. Current status: {project_metadata.status}")
            else:
                say_error(f"Failed to load project {selected_project_id}. Starting new session.")
                selected_project_id = None

        else:
            # New project: perform initial web search and store results
            say_system("Starting a new project. Performing initial research...")
            
            # ... (web search code - currently commented out) ...
            
            # After setting up a new project, wait for the first actual user query
            say_system("New project started. What would you like to build?")

        while True:
            try:
                user_input = console.input("[bold blue]💭 You > [/bold blue]").strip()

                if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                    say_system(
                        "👋 Thanks for brainstorming! Come back anytime with new ideas."
                    )
                    break

                if user_input.lower() == "clear history":
                    self.state_manager.clear_conversation_history(user_id)
                    say_system("Conversation history cleared.")
                    continue

                if not user_input:
                    continue

                # Only process query if it's not the "new" command itself
                if user_input.lower() == "new" and selected_project_id is None:
                    say_error("You've already started a new project. Please provide your idea.")
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