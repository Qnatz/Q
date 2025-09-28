# tools/base_tool_classes.py
"""
Base tool classes and schemas
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ToolType(Enum):
    SEARCH = "search"
    FILE_OPERATION = "file_operation"
    CODE_ANALYSIS = "code_analysis"
    SYSTEM_INFO = "system_info"
    REPLACEMENT = "replacement"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"

class ToolExecutionStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"

class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]
    tool_type: ToolType
    keywords: List[str]
    examples: List[Dict[str, Any]]

class ToolResult:
    def __init__(self, status: ToolExecutionStatus, result: Any = None, 
                 error_message: str = None, metadata: Dict[str, Any] = None,
                 execution_time: float = 0.0):
        self.status = status
        self.result = result
        self.error_message = error_message
        self.metadata = metadata or {}
        self.execution_time = execution_time

class BaseTool:
    def __init__(self):
        self.schema = self._define_schema()
    
    def _define_schema(self) -> ToolSchema:
        raise NotImplementedError("Subclasses must implement _define_schema")
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters against schema"""
        # Basic validation logic
        for required_param in self.schema.required:
            if required_param not in parameters:
                return False
        return True
    
    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        raise NotImplementedError("Subclasses must implement execute")