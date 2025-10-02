import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch

from agent_processes.programming_module import ProgrammingModule
from tools.tool_registry import ToolRegistry, ToolResult, ToolExecutionStatus
from tools.base_tool_classes import BaseTool

class MockStepwiseTool(BaseTool):
    def __init__(self):
        self.schema = MagicMock()
        self.schema.name = "stepwise_implementation"

    def execute(self, parameters, context=None):
        return ToolResult(
            status=ToolExecutionStatus.SUCCESS,
            result=[{"file_path": "test_output.txt", "content": "Hello, World!"}]
        )

@pytest.fixture
def mock_llm_service():
    return MagicMock()

@pytest.fixture
def mock_prompt_manager():
    return MagicMock()

@pytest.fixture
def mock_tool_registry(mock_llm_service):
    registry = ToolRegistry(llm=mock_llm_service)
    # Unregister the real stepwise tool to replace it with a mock
    registry.unregister_tool("stepwise_implementation")
    registry.register_tool(MockStepwiseTool())
    return registry

def test_implement_writes_file(mock_llm_service, mock_prompt_manager, mock_tool_registry):
    """
    Test that the implement method correctly calls the file_operation tool
    and a file is created.
    """
    module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry)
    
    plan = {
        "tasks": [{"task": "Create a file", "description": "Write a file"}]
    }
    project_title = "Test Project"
    
    # The implement method is a generator. We need to consume it.
    for result in module.implement(plan, project_title):
        pass

    # Check if the file was written
    assert os.path.exists("test_output.txt")
    
    with open("test_output.txt", "r") as f:
        content = f.read()
        assert content == "Hello, World!"
        
    # Clean up the file
    os.remove("test_output.txt")

@patch('tools.tool_registry.ToolRegistry.execute_tool')
def test_run_command_with_timeout_mocked(mock_execute_tool, mock_llm_service, mock_prompt_manager, mock_tool_registry):
    """
    Test that the _run_command_with_timeout method calls execute_tool with the correct parameters.
    """
    mock_execute_tool.return_value = ToolResult(
        status=ToolExecutionStatus.SUCCESS,
        result={"exit_code": 0, "stdout": "Hello from shell\n", "stderr": ""}
    )
    
    module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry)
    
    command = ["echo", "Hello from shell"]
    description = "A simple echo command"
    
    result = module._run_command_with_timeout(command, description)
    
    mock_execute_tool.assert_called_once_with(
        'run_shell_command',
        parameters={'command': 'echo Hello from shell', 'description': description, 'timeout': 300, 'cwd': None}
    )
    
    assert result is not None
    assert result["exit_code"] == 0
    assert result["stdout"] == "Hello from shell\n"
    assert result["stderr"] == ""