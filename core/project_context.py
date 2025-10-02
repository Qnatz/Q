# project_context.py
from typing import List, Dict

class ProjectContext:
    def __init__(self, project_data_source):
        """
        project_data_source could be your database, JSON files, or any project metadata provider.
        """
        self.project_data_source = project_data_source

    def get_conversation_history(self, project_id: str) -> List[Dict[str, str]]:
        """
        Returns project-specific context formatted for the planner:
        [{'role': 'system'|'user', 'content': '...'}, ...]
        """
        history = []

        # Example: add project metadata
        metadata = self.project_data_source.get_project_metadata(project_id)
        if metadata:
            history.append({
                "role": "system",
                "content": f"Project metadata: {metadata}"
            })

        # Example: add file and module info
        files = self.project_data_source.get_project_files(project_id)
        if files:
            history.append({
                "role": "system",
                "content": f"Project files and structure: {files}"
            })

        # Example: add previous tasks, tickets, or notes
        tasks = self.project_data_source.get_project_tasks(project_id)
        if tasks:
            history.append({
                "role": "system",
                "content": f"Previous tasks and status: {tasks}"
            })

        return history
