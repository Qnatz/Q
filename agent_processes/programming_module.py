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

class ProgrammingModule:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager, tool_registry: ToolRegistry, state_manager: Any):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.tool_registry = tool_registry
        self.state_manager = state_manager
        self.language_configs: Dict[str, Dict[str, Any]] = self._get_language_configs()

    def _get_language_configs(self) -> Dict[str, Dict[str, Any]]:
        """Configuration for different programming languages."""
        return {
            'python': {
                'style_guide': 'PEP 8',
                'testing_framework': 'pytest',
                'package_manager': 'pip',
                'guidance': 'Follow Python PEP 8 and packaging best practices.'
            },
            'javascript': {
                'style_guide': 'ESLint/Prettier',
                'testing_framework': 'Jest',
                'package_manager': 'npm/yarn',
                'guidance': 'Follow JavaScript/TypeScript best practices and npm conventions.'
            },
            'java': {
                'style_guide': 'Google Java Style',
                'testing_framework': 'JUnit',
                'package_manager': 'Maven/Gradle',
                'guidance': 'Follow Java best practices and Maven/Gradle conventions.'
            },
            'kotlin': {
                'style_guide': 'Kotlin Coding Conventions',
                'testing_framework': 'JUnit/Kotest',
                'package_manager': 'Gradle/Maven',
                'guidance': 'Follow Kotlin best practices and Gradle conventions.'
            },
            # Add other languages as needed
        }

    def _detect_language(self, plan: Dict[str, Any], project_title: str) -> str:
        """Detect programming language from the plan and project title."""
        text_to_analyze = project_title + " " + " ".join([task.get('description', '') for task in plan.get('tasks', [])])
        text_lower = text_to_analyze.lower()
        
        language_mentions = {
            'python': ['python', 'py', 'django', 'flask', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', 'typescript', 'ts'],
            'java': ['java', 'spring', 'maven', 'gradle', 'jvm'],
            'kotlin': ['kotlin', 'kt', 'android', 'jetbrains'],
        }
        
        for lang, indicators in language_mentions.items():
            if any(indicator in text_lower for indicator in indicators):
                return lang
        
        return 'python'  # Default fallback

    def implement(self, plan: Dict[str, Any], project_title: str, user_id: str, project_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Implement project tasks using a generator to stream progress.
        """
        tasks = plan.get("tasks", [])
        if not tasks:
            yield {"type": "complete", "status": "success", "message": "No tasks to implement."}
            return

        logger.info(f"Starting implementation of {len(tasks)} tasks.")

        # Update programmer status to 'running'
        self.state_manager.set_module_status(user_id, project_id, "programmer", "running")

        try:
            system_prompt_template = self.prompt_manager.get_prompt("orchestrator_programming_phase_prompt")
            if not system_prompt_template:
                yield {"type": "implementation_error", "status": "error", "message": "Programming prompt not found."}
                return

            detected_language = self._detect_language(plan, project_title)
            language_guidance = self.language_configs.get(detected_language, {}).get('guidance', '')

            all_implemented_files = []
            for i, task in enumerate(tasks):
                logger.info(f"Implementing task {i+1}/{len(tasks)}: {task.get('task')}")

                # TODO: Get dynamic context like codebase_tree, dependencies_installed, etc.
                formatted_system_prompt = system_prompt_template.format(
                    PLAN_PROMPT=task.get('description', ''),
                    CUSTOM_RULES=language_guidance,
                    PLAN_GENERATION_NOTES="",
                    REPO_DIRECTORY="/root/Q",
                    DEPENDENCIES_INSTALLED_PROMPT="false",
                    CODEBASE_TREE=""
                )

                try:
                    tool_result = self.tool_registry.execute_tool(
                        "stepwise_implementation", 
                        parameters={
                            "task": task,
                            "project_title": project_title,
                            "system_instruction": formatted_system_prompt
                        },
                        context={"project_title": project_title, "plan": plan}
                    )

                    if tool_result.status == ToolExecutionStatus.SUCCESS:
                        implemented_files = tool_result.result
                        all_implemented_files.extend(implemented_files)
                        yield {"type": "task_complete", "status": "success", "task": task.get('task'), "files": implemented_files}
                    else:
                        yield {"type": "task_error", "status": "error", "task": task.get('task'), "message": tool_result.error_message}
                        # Optionally, decide if you want to stop the entire process on a single task failure
                        # return

                except Exception as e:
                    logger.error(f"Error during stepwise implementation of task {task.get('task')}: {e}")
                    yield {"type": "task_error", "status": "error", "task": task.get('task'), "message": str(e)}
                    # Optionally, decide if you want to stop the entire process on a single task failure
                    # return
            
            yield {"type": "implementation_complete", "status": "success", "files": all_implemented_files}

        finally:
            # Ensure programmer status is set to 'idle' when implementation is complete or an error occurs
            self.state_manager.set_module_status(user_id, project_id, "programmer", "idle")
