# programming_module.py
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass
import logging

from core.llm_service import LLMService
from memory.prompt_manager import PromptManager
from tools.tool_registry import ToolRegistry, ToolExecutionStatus

logger = logging.getLogger(__name__)

@dataclass
class ImplementationResult:
    success: bool
    implemented_files: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

class ProgrammingModule:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager, tool_registry: ToolRegistry, state_manager: any):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.tool_registry = tool_registry
        self.state_manager = state_manager
    
    def implement(self, plan: Dict[str, Any], project_title: str, user_id: str, project_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Optimized implementation with streaming and parallel execution where possible.
        """
        tasks = plan.get("tasks", [])
        if not tasks:
            yield {"type": "complete", "status": "success", "message": "No tasks to implement."}
            return

        logger.info(f"Starting optimized implementation of {len(tasks)} tasks.")

        state = self.state_manager.get_conversation_state(user_id, project_id)
        state.module_status["programmer"] = "running"
        self.state_manager.update_conversation_state(user_id, state, project_id)

        try:
            quick_tasks = []
            code_tasks = []
            
            for task in tasks:
                if self._is_quick_task(task):
                    quick_tasks.append(task)
                else:
                    code_tasks.append(task)

            for task in quick_tasks:
                yield from self._execute_quick_task(task, project_title, project_id)

            for task in code_tasks:
                yield from self._execute_code_task(task, project_title, project_id, plan)

            yield {"type": "implementation_complete", "status": "success", "files": self._get_all_files(project_id)}

        finally:
            state = self.state_manager.get_conversation_state(user_id, project_id)
            state.module_status["programmer"] = "idle"
            self.state_manager.update_conversation_state(user_id, state, project_id)

    def _is_quick_task(self, task: Dict[str, Any]) -> bool:
        """Identify tasks that can be processed quickly"""
        task_desc = (task.get('task', '') + task.get('description', '')).lower()
        quick_keywords = ['requirements', 'readme', 'config', 'setup', 'documentation', 'gitignore']
        return any(keyword in task_desc for keyword in quick_keywords)

    def _execute_quick_task(self, task: Dict, project_title: str, project_id: str) -> Generator[Dict, None, None]:
        """Execute quick tasks with optimized prompts"""
        try:
            simplified_prompt = f"Create {task.get('task')} for {project_title}. Be concise."

            tool_result = self.tool_registry.execute_tool(
                "stepwise_implementation",
                parameters={
                    "task": task,
                    "project_title": project_title,
                    "system_instruction": simplified_prompt,
                    "project_id": project_id.lower(),
                    "implemented_files": []
                }
            )

            if tool_result.status == ToolExecutionStatus.SUCCESS:
                files = [f['file_path'] for f in tool_result.result] if tool_result.result else []
                yield {"type": "task_complete", "status": "success", "task": task.get('task'), "files": files, "quick": True}
            else:
                yield {"type": "task_error", "status": "error", "task": task.get('task'), "message": tool_result.error_message}

        except Exception as e:
            logger.error(f"Error in quick task {task.get('task')}: {e}")
            yield {"type": "task_error", "status": "error", "task": task.get('task'), "message": str(e)}

    def _execute_code_task(self, task: Dict, project_title: str, project_id: str, plan: Dict) -> Generator[Dict, None, None]:
        """Execute code implementation tasks with progress streaming"""
        yield {"type": "task_start", "status": "running", "task": task.get('task')}
        
        try:
            system_prompt = self._build_system_prompt(task, project_title, plan)
            
            tool_result = self.tool_registry.execute_tool(
                "stepwise_implementation",
                parameters={
                    "task": task,
                    "project_title": project_title,
                    "system_instruction": system_prompt,
                    "project_id": project_id.lower(),
                    "implemented_files": self._get_current_files(project_id)
                }
            )

            if tool_result.status == ToolExecutionStatus.SUCCESS:
                files = [f['file_path'] for f in tool_result.result] if tool_result.result else []
                yield {"type": "task_complete", "status": "success", "task": task.get('task'), "files": files}
            else:
                yield {"type": "task_error", "status": "error", "task": task.get('task'), "message": tool_result.error_message}

        except Exception as e:
            logger.error(f"Error in code task {task.get('task')}: {e}")
            yield {"type": "task_error", "status": "error", "task": task.get('task'), "message": str(e)}

    def _get_all_files(self, project_id: str) -> List[str]:
        """Get all files in the project directory"""
        project_dir = Path(f"/root/Q/projects/{project_id.lower()}")
        if not project_dir.is_dir():
            return []
        return [str(p.relative_to(project_dir)) for p in project_dir.rglob("*") if p.is_file()]

    def _get_current_files(self, project_id: str) -> List[str]:
        """Get all files in the project directory"""
        return self._get_all_files(project_id)

    def _build_system_prompt(self, task: Dict, project_title: str, plan: Dict) -> str:
        """Build the system prompt for the programmer"""
        # This is a placeholder. In a real implementation, this would be more sophisticated.
        return f"You are a programmer working on a project called {project_title}. Your task is to implement the following: {task.get('description')}"