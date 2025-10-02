import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from tools.shell_tool import ShellTool
from tools.base_tool_classes import ToolResult, ToolExecutionStatus

def test_shell_tool_success():
    """Test that the ShellTool can successfully execute a command."""
    tool = ShellTool()
    parameters = {"command": "echo 'Hello, World!'"}
    result = tool.execute(parameters)
    
    assert isinstance(result, ToolResult)
    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.result["stdout"] == "Hello, World!\n"
    assert result.result["stderr"] == ""
    assert result.result["exit_code"] == 0

def test_shell_tool_error():
    """Test that the ShellTool handles a command that produces an error."""
    tool = ShellTool()
    parameters = {"command": "ls non_existent_directory"}
    result = tool.execute(parameters)
    
    assert isinstance(result, ToolResult)
    assert result.status == ToolExecutionStatus.SUCCESS # The tool itself succeeds, but the command fails
    assert result.result["stdout"] == ""
    assert "No such file or directory" in result.result["stderr"]
    assert result.result["exit_code"] != 0
