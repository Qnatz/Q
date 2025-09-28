import os
import sys
import argparse

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_config import setup_logging
setup_logging()

from core.settings import settings
from core.orchestrator import OrchestratorAgent

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--online", action="store_true", help="Use online LLM mode (Gemini).")
    group.add_argument("--offline", action="store_true", help="Use offline LLM mode (local).")
    args = parser.parse_args()

    if args.online:
        settings.llm_mode = "online"
    elif args.offline:
        settings.llm_mode = "offline"
        
    try:
        orchestrator = OrchestratorAgent()

        if settings.prompt:
            from core.ui import say_user

            say_user(settings.prompt)
            orchestrator.process_query(settings.prompt, "default_user")
        else:
            from core.ui import say_assistant
            welcome_message = (
                "🎯 **AI Solution Architect**\n\n"
                "I transform your ideas into working software! Just tell me:\n"
                "• What problem you're trying to solve\n"
                "• What you wish existed\n"
                "• Any workflow you want to automate\n\n"
                "I'll handle all the technical details. What's on your mind?"
            )
            say_assistant(welcome_message)
            orchestrator.run()

    except Exception as e:
        from core.ui import say_error

        say_error(f"Failed to start orchestrator: {e}")
        sys.exit(1)