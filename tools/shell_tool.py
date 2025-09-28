import subprocess
import logging
from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ShellTool(BaseTool):
    """Shell command execution tool"""

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="run_shell_command",
            description="Executes a shell command.",
            parameters={
                "command": {"type": "string", "description": "The shell command to execute."},
            },
            required=["command"],
            tool_type=ToolType.SYSTEM_INFO,
            keywords=["shell", "command", "execute", "run"],
            examples=[
                {"command": "ls -l"},
                {"command": "echo 'Hello, World!'"},
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
            
            command = parameters["command"]
            
            process = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result={
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode,
                },
                metadata={"command": command},
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Shell command execution failed: {e}")
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
