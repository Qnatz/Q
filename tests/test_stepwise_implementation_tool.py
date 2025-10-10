import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.builtin_tools.stepwise_implementation_tool import StepwiseImplementationTool, ToolResult, ToolExecutionStatus

@pytest.fixture
def mock_llm_service():
    """Fixture for a mock LLM service."""
    return MagicMock()

@pytest.fixture
def mock_tool_registry():
    """Fixture for a mock tool registry."""
    return MagicMock()

def test_stepwise_implementation_tool_initialization(mock_llm_service, mock_tool_registry):
    """Test that the StepwiseImplementationTool initializes correctly."""
    tool = StepwiseImplementationTool(llm_service=mock_llm_service, tool_registry=mock_tool_registry)
    assert tool is not None

@patch("tools.builtin_tools.stepwise_implementation_tool.StepwiseImplementationTool._should_skip_build_test", return_value=True)
def test_stepwise_implementation_tool_execute(mock_should_skip, mock_llm_service, mock_tool_registry):
    """Test the execute method of the StepwiseImplementationTool."""
    tool = StepwiseImplementationTool(llm_service=mock_llm_service, tool_registry=mock_tool_registry)
    
    # Mock the LLM response
    mock_llm_service.generate_with_plan.return_value = '{"files": [{"file_path": "test.py", "action": "create", "content": "print(\'hello\')"}]}'

    # Mock the file write operation in the tool_registry
    mock_tool_registry.execute_tool.return_value = ToolResult(
        status=ToolExecutionStatus.SUCCESS,
        result={"success": True}
    )
    
    parameters = {
        "task": {"task": "Create a hello world script.", "description": "Create a python script that prints hello."},
        "project_title": "My Project",
        "system_instruction": "Use python.",
        "project_id": "test-project"
    }
    
    result = tool.execute(parameters)
    
    assert isinstance(result, ToolResult)
    assert result.status == ToolExecutionStatus.SUCCESS
    assert len(result.result) == 1
    assert result.result[0]["file_path"] == "test.py"

    # Verify that the correct tool was called for writing the file
    mock_tool_registry.execute_tool.assert_called_once_with(
        'file_operation',
        parameters={
            'operation': 'write',
            'path': '/root/Q/projects/test-project/test.py',
            'content': "print('hello')",
            'overwrite': True,
            'create_parents': True
        },
        context={'project_id': 'test-project'}
    )