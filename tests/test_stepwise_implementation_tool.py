import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch

from tools.builtin_tools.stepwise_implementation_tool import StepwiseImplementationTool, ToolResult, ToolExecutionStatus

@pytest.fixture
def mock_llm():
    return MagicMock()

def test_stepwise_implementation_tool_initialization(mock_llm):
    """Test that the StepwiseImplementationTool initializes correctly."""
    tool = StepwiseImplementationTool(llm=mock_llm)
    assert tool is not None

@patch("tools.builtin_tools.stepwise_implementation_tool.StepwiseImplementationTool._is_build_required_for_task", return_value=False)
def test_stepwise_implementation_tool_execute(mock_is_build_required, mock_llm):
    """Test the execute method of the StepwiseImplementationTool."""
    tool = StepwiseImplementationTool(llm=mock_llm)
    
    # Mock the LLM response
    mock_llm.generate.return_value = "{\"files\": [{\"file_path\": \"test.py\", \"content\": \"print('hello')\"}]}"
    
    parameters = {
        "task": {"task": "Create a hello world script.", "description": "Create a python script that prints hello."},
        "project_title": "My Project",
        "system_instruction": "Use python."
    }
    
    result = tool.execute(parameters)
    
    assert isinstance(result, ToolResult)
    assert result.status == ToolExecutionStatus.SUCCESS
    assert len(result.result) == 1
    assert result.result[0]["file_path"] == "test.py"
