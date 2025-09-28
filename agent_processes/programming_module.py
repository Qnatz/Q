# programming_module.py
import json
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass
import logging
import os

from qllm.unified_llm import UnifiedLLM
from schemas.implementation_schema import IMPLEMENTATION_SCHEMA
from utils.json_utils import safe_json_extract
from utils.validation_utils import validate
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
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager, tool_registry: ToolRegistry):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.tool_registry = tool_registry

    def implement(self, plan: Dict[str, Any], project_title: str) -> Generator[Dict[str, Any], None, None]:
        """
        Implement project tasks using a generator to stream progress.
        """
        tasks = plan.get("tasks", [])
        if not tasks:
            yield {"type": "complete", "status": "success", "message": "No tasks to implement."}
            return

        logger.info(f"Starting implementation of {len(tasks)} tasks.")
        
        try:
            tool_result = self.tool_registry.execute_tool(
                "stepwise_implementation", 
                parameters={"tasks": tasks, "project_title": project_title}
            )

            if tool_result.status == ToolExecutionStatus.SUCCESS:
                for result in tool_result.result:
                    yield result
            else:
                yield {"type": "error", "message": f"Implementation failed: {tool_result.error_message}"}

        except Exception as e:
            logger.error(f"Error during stepwise implementation: {e}")
            yield {"type": "error", "message": f"Implementation failed: {e}"}