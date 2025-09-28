import logging
from core.git_service import GitService
from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GitTool(BaseTool):
    """Git operations tool"""

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="git_operation",
            description="Perform Git operations on the repository.",
            parameters={
                "operation": {"type": "string", "enum": ["status", "diff", "log", "add", "commit"], "description": "The Git operation to perform."},
                "paths": {"type": "array", "items": {"type": "string"}, "description": "List of file paths for the 'add' operation."},
                "message": {"type": "string", "description": "Commit message for the 'commit' operation."},
                "cached": {"type": "boolean", "description": "Get the cached diff for the 'diff' operation."},
                "count": {"type": "integer", "description": "Number of logs to retrieve for the 'log' operation."},
            },
            required=["operation"],
            tool_type=ToolType.CUSTOM,
            keywords=["git", "version control", "commit", "diff", "status", "log", "add"],
            examples=[
                {"operation": "status"},
                {"operation": "diff"},
                {"operation": "log", "count": 5},
                {"operation": "add", "paths": ["file1.txt", "file2.txt"]},
                {"operation": "commit", "message": "Initial commit"},
            ]
        )

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            operation = parameters["operation"]
            git_service = GitService()

            result = None
            if operation == "status":
                result = git_service.get_status()
            elif operation == "diff":
                cached = parameters.get("cached", False)
                result = git_service.get_diff(cached=cached)
            elif operation == "log":
                count = parameters.get("count", 10)
                result = git_service.get_log(count=count)
            elif operation == "add":
                paths = parameters.get("paths", [])
                if not paths:
                    logger.error("'paths' parameter is required for 'add' operation.")
                    return ToolResult(
                        status=ToolExecutionStatus.VALIDATION_ERROR,
                        result=None,
                        error_message="'paths' parameter is required for 'add' operation."
                    )
                result = git_service.add(paths)
            elif operation == "commit":
                message = parameters.get("message")
                if not message:
                    logger.error("'message' parameter is required for 'commit' operation.")
                    return ToolResult(
                        status=ToolExecutionStatus.VALIDATION_ERROR,
                        result=None,
                        error_message="'message' parameter is required for 'commit' operation."
                    )
                result = git_service.commit(message)
            else:
                logger.error(f"Unknown operation: {operation}")
                raise ValueError(f"Unknown operation: {operation}")
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=result,
                metadata={"operation": operation},
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Git operation failed: {e}")
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )