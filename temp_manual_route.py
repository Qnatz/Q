import sys
sys.path.append('/root/Q')
from core.orchestrator import OrchestratorAgent

orchestrator = OrchestratorAgent()
response_dict = {
    'type': 'ideation',
    'message': 'Build an Android app in Kotlin using Jetpack Compose and Room. - One table: Notes(id, text) - Main screen shows all notes - FloatingActionButton opens dialog to add new note'
}
user_id = 'default_user'
orchestrator.response_handler.handle_response(response_dict, user_id)
