import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ProjectContext:
    def __init__(self, project_data_source):
        """
        project_data_source is expected to be a UnifiedMemory instance
        that provides access to project metadata and information.
        """
        self.project_data_source = project_data_source

    def get_conversation_history(self, project_id: str) -> List[Dict[str, str]]:
        """
        Returns project-specific context formatted for the planner:
        [{'role': 'system'|'user', 'content': '...'}, ...]
        """
        if not project_id:
            logger.warning("No project_id provided to get_conversation_history")
            return []
            
        history = []

        try:
            # Get project metadata
            metadata = self._get_project_metadata(project_id)
            if metadata:
                history.append({
                    "role": "system",
                    "content": f"Project metadata: {self._format_metadata(metadata)}"
                })

            # Get file and module info
            files = self._get_project_files(project_id)
            if files:
                history.append({
                    "role": "system",
                    "content": f"Project files and structure: {self._format_files(files)}"
                })

            # Get previous tasks, tickets, or notes
            tasks = self._get_project_tasks(project_id)
            if tasks:
                history.append({
                    "role": "system",
                    "content": f"Previous tasks and status: {self._format_tasks(tasks)}"
                })

        except Exception as e:
            logger.error(f"Error getting conversation history for project {project_id}: {e}")

        return history

    def _get_project_metadata(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Safely retrieve project metadata"""
        try:
            if hasattr(self.project_data_source, 'get_project_metadata'):
                return self.project_data_source.get_project_metadata(project_id)
            elif hasattr(self.project_data_source, 'tinydb'):
                # Fallback to TinyDB if available
                return self.project_data_source.tinydb.get_project_metadata(project_id)
            else:
                logger.warning("project_data_source has no method to get project metadata")
                return None
        except Exception as e:
            logger.error(f"Error retrieving project metadata: {e}")
            return None

    def _get_project_files(self, project_id: str) -> Optional[List[Dict[str, Any]]]:
        """Safely retrieve project files"""
        try:
            # Try various possible methods
            if hasattr(self.project_data_source, 'get_project_files'):
                return self.project_data_source.get_project_files(project_id)
            elif hasattr(self.project_data_source, 'tinydb'):
                db = self.project_data_source.tinydb
                if hasattr(db, 'get_project_files'):
                    return db.get_project_files(project_id)
            
            # Fallback: try to get from metadata
            metadata = self._get_project_metadata(project_id)
            if metadata and 'files' in metadata:
                return metadata.get('files', [])
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving project files: {e}")
            return None

    def _get_project_tasks(self, project_id: str) -> Optional[List[Dict[str, Any]]]:
        """Safely retrieve project tasks"""
        try:
            if hasattr(self.project_data_source, 'get_project_tasks'):
                return self.project_data_source.get_project_tasks(project_id)
            elif hasattr(self.project_data_source, 'tinydb'):
                db = self.project_data_source.tinydb
                if hasattr(db, 'get_project_tasks'):
                    return db.get_project_tasks(project_id)
            
            # Fallback: try to get from metadata
            metadata = self._get_project_metadata(project_id)
            if metadata and 'tasks' in metadata:
                return metadata.get('tasks', [])
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving project tasks: {e}")
            return None

    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for display"""
        if not metadata:
            return "No metadata available"
        
        # Extract key fields
        formatted = []
        for key in ['project_name', 'status', 'description', 'completion_rate']:
            if key in metadata:
                formatted.append(f"{key}: {metadata[key]}")
        
        return ", ".join(formatted) if formatted else str(metadata)

    def _format_files(self, files: List[Dict[str, Any]]) -> str:
        """Format file list for display"""
        if not files:
            return "No files available"
        
        try:
            file_list = []
            for f in files[:20]:  # Limit to first 20 files
                if isinstance(f, dict):
                    name = f.get('name') or f.get('path') or f.get('file_path', 'unknown')
                    file_list.append(name)
                else:
                    file_list.append(str(f))
            
            result = ", ".join(file_list)
            if len(files) > 20:
                result += f" (and {len(files) - 20} more)"
            
            return result
        except Exception as e:
            logger.error(f"Error formatting files: {e}")
            return f"{len(files)} files"

    def _format_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        """Format task list for display"""
        if not tasks:
            return "No tasks available"
        
        try:
            task_list = []
            for t in tasks[:10]:  # Limit to first 10 tasks
                if isinstance(t, dict):
                    desc = t.get('description') or t.get('task') or t.get('title', 'unknown task')
                    status = t.get('status', 'unknown')
                    task_list.append(f"{desc} ({status})")
                else:
                    task_list.append(str(t))
            
            result = "; ".join(task_list)
            if len(tasks) > 10:
                result += f" (and {len(tasks) - 10} more)"
            
            return result
        except Exception as e:
            logger.error(f"Error formatting tasks: {e}")
            return f"{len(tasks)} tasks"
