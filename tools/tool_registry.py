# tools/tool_registry.py
"""
Tool Registry System - Dynamic function calling for QAI Agent
Provides extensible tool system with schema validation and execution
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from tools.base_tool_classes import BaseTool, ToolResult, ToolExecutionStatus
from tools.builtin_tools.web_search_tool import WebSearchTool
from tools.builtin_tools.file_operation_tool import FileOperationTool
from tools.builtin_tools.code_analysis_tool import CodeAnalysisTool
from tools.builtin_tools.system_info_tool import SystemInfoTool
from tools.builtin_tools.robust_replace_tool import RobustReplaceTool
from tools.builtin_tools.stepwise_planner_tool import StepwisePlannerTool
from tools.builtin_tools.stepwise_implementation_tool import StepwiseImplementationTool
from tools.builtin_tools.stepwise_qa_tool import StepwiseQATool
from tools.builtin_tools.stepwise_review_tool import StepwiseReviewTool
from tools.builtin_tools.git_tool import GitTool
from tools.builtin_tools.shell_tool import ShellTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Main tool registry for managing and executing tools
    """
    
    def __init__(self, config_path: Optional[str] = None, llm: Any = None, llm_service: Any = None):
        self.tools: Dict[str, BaseTool] = {}
        self.config_path = config_path or "config/tools.yaml"
        self.execution_history: List[Dict[str, Any]] = []
        self.llm = llm # This is UnifiedLLM
        self.llm_service = llm_service # This is LLMService
        
        self._register_builtin_tools()
        self._load_custom_tools()
        
        logger.info(f"Tool registry initialized with {len(self.tools)} tools")
    
    def _register_builtin_tools(self):
        """Register built-in tools"""
        builtin_tools = [
            WebSearchTool(),
            FileOperationTool(),
            CodeAnalysisTool(),
            SystemInfoTool(),
            RobustReplaceTool(),
            GitTool(),
            ShellTool(),
            StepwisePlannerTool(llm=self.llm_service), # Use LLMService
            StepwiseImplementationTool(self.llm_service, tool_registry=self), # Use LLMService
            StepwiseQATool(llm_service=self.llm_service, tool_registry=self),
            StepwiseReviewTool(llm_service=self.llm_service, tool_registry=self)
        ]
        
        for tool in builtin_tools:
            self.register_tool(tool)
    
    def _load_custom_tools(self):
        """Load custom tools from configuration"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                # Load and register custom tools from config
                pass
        except Exception as e:
            logger.warning(f"Failed to load custom tools: {e}")
    
    def register_tool(self, tool: BaseTool) -> bool:
        """Register a new tool"""
        try:
            self.tools[tool.schema.name] = tool
            logger.info(f"Registered tool: {tool.schema.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register tool {tool.schema.name}: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                    context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Tool '{tool_name}' not found"
            )
        
        try:
            tool = self.tools[tool_name]
            result = tool.execute(parameters, context)
            
            self.execution_history.append({
                "tool_name": tool_name,
                "parameters": parameters,
                "result_status": result.status.value,
                "execution_time": result.execution_time,
                "timestamp": time.time()
            })
            
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            logger.info(f"Executed tool {tool_name}: {result.status.value}")
            return result
            
        except Exception as e:
            error_result = ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Tool execution failed: {str(e)}"
            )
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return error_result
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool"""
        if tool_name in self.tools:
            return self.tools[tool_name].schema.to_dict()
        return None
    
    def list_tools(self, tool_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available tools, optionally filtered by type"""
        tools_info = []
        
        for tool_name, tool in self.tools.items():
            if tool_type is None or tool.schema.tool_type.value == tool_type:
                tools_info.append({
                    "name": tool_name,
                    "description": tool.schema.description,
                    "type": tool.schema.tool_type.value,
                    "keywords": tool.schema.keywords
                })
        
        return tools_info
    
    def find_tools_by_keywords(self, keywords: List[str]) -> List[str]:
        """Find tools that match given keywords"""
        matching_tools = []
        
        for tool_name, tool in self.tools.items():
            tool_keywords = [kw.lower() for kw in tool.schema.keywords]
            if any(keyword.lower() in tool_keywords for keyword in keywords):
                matching_tools.append(tool_name)
        
        return matching_tools
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_history:
            return {"total_executions": 0}
        
        stats = {
            "total_executions": len(self.execution_history),
            "successful_executions": sum(1 for h in self.execution_history if h["result_status"] == "success"),
            "failed_executions": sum(1 for h in self.execution_history if h["result_status"] == "error"),
            "average_execution_time": sum(h.get("execution_time", 0) for h in self.execution_history) / len(self.execution_history)
        }
        
        tool_usage = {}
        for h in self.execution_history:
            tool_name = h["tool_name"]
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        
        stats["most_used_tools"] = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return stats

# Integration with Unified Memory
def create_tool_aware_memory_integration(memory_instance, registry_instance):
    """Create integration between tool registry and unified memory"""
    
    def enhanced_tool_execution(tool_name: str, parameters: Dict[str, Any], 
                              context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Execute tool and automatically store results in memory"""
        # Execute tool
        result = registry_instance.execute_tool(tool_name, parameters, context)
        
        if result.status == ToolExecutionStatus.SUCCESS:
            from memory.unified_memory import MemoryType
            memory_instance.store_tool_result(
                tool_name=tool_name,
                result=json.dumps(result.result),
                user_id=context.get("user_id", "system") if context else "system",
                metadata={
                    "parameters": json.dumps(parameters),
                    "execution_time": result.execution_time,
                    "status": result.status.value
                }
            )
        
        return result
    
    registry_instance.execute_tool_with_memory = enhanced_tool_execution
    return registry_instance

# Factory functions
def create_default_tool_registry(llm: Any = None, llm_service: Any = None) -> ToolRegistry:
    """Create a tool registry with all built-in tools"""
    return ToolRegistry(llm=llm, llm_service=llm_service)

def create_minimal_tool_registry(llm: Any = None) -> ToolRegistry:
    """Create a minimal tool registry with only essential tools"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry.tools = {}
    registry.execution_history = []
    registry.llm = llm
    
    registry.register_tool(FileOperationTool())
    registry.register_tool(SystemInfoTool())
    
    return registry

if __name__ == "__main__":
    # Example usage
    from memory.unified_memory import UnifiedMemory
    
    class MockLLM:
        def generate_with_plan(self, prompt, system_instruction=None, chunk_size=512, step_size=256):
            print(f"MockLLM generating for prompt: {prompt[:50]}...")
            if "plan" in prompt.lower():
                return json.dumps({"tasks": [{"task": "Mock Plan Task", "description": "Mock Description"}], "files": []})
            else:
                return json.dumps({"files": [{"file_path": "mock_file.txt", "action": "created"}]})

    mock_llm = MockLLM()
    
    # Create a UnifiedMemory instance
    memory = UnifiedMemory()
    
    # Create registry
    registry = create_default_tool_registry(llm=mock_llm)
    
    # Integrate with UnifiedMemory
    registry = create_tool_aware_memory_integration(memory, registry)
    
    # List available tools
    print("Available tools:")
    for tool_info in registry.list_tools():
        print(f"  - {tool_info['name']}: {tool_info['description']}")
