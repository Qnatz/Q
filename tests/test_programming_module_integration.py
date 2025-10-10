import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_processes.programming_module import ProgrammingModule
from tools.tool_registry import ToolRegistry, ToolResult, ToolExecutionStatus
from tools.base_tool_classes import BaseTool

class MockStepwiseTool(BaseTool):
    """A mock tool that simulates writing a file."""
    def __init__(self):
        self.schema = MagicMock()
        self.schema.name = "stepwise_implementation"

    def execute(self, parameters, context=None):
        # Simulate the tool's behavior by creating the file
        file_path = "test_output.txt"
        content = "Hello, World!"
        with open(file_path, "w") as f:
            f.write(content)

        return ToolResult(
            status=ToolExecutionStatus.SUCCESS,
            result=[{"file_path": file_path, "content": content}]
        )

@pytest.fixture
def mock_llm_service():
    return MagicMock()

@pytest.fixture
def mock_prompt_manager():
    return MagicMock()

@pytest.fixture
def mock_state_manager():
    """Fixture for a mock state manager."""
    state_manager = MagicMock()
    state = MagicMock()
    state.module_status = {"programmer": "idle"}
    state_manager.get_conversation_state.return_value = state
    return state_manager

@pytest.fixture
def mock_tool_registry(mock_llm_service):
    """Fixture for a tool registry with a mock stepwise_implementation tool."""
    registry = ToolRegistry(llm=mock_llm_service)
    # Unregister the real tool if it exists and register our mock
    if "stepwise_implementation" in registry.tools:
        registry.unregister_tool("stepwise_implementation")
    registry.register_tool(MockStepwiseTool())
    return registry

def test_implement_writes_file(mock_llm_service, mock_prompt_manager, mock_tool_registry, mock_state_manager):
    """
    Test that the implement method correctly calls the file_operation tool
    and a file is created as a result.
    """
    with patch('pathlib.Path.is_dir', return_value=True), \
         patch('pathlib.Path.rglob', return_value=[]):

        module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry, mock_state_manager)

        plan = {"tasks": [{"task": "Create a file", "description": "Write a file"}]}
        project_title = "Test Project"
        user_id = "test_user"
        project_id = "test_project"

        # The implement method is a generator. We need to consume it.
        results = list(module.implement(plan, project_title, user_id, project_id))

        # Check if the file was written by our mock tool
        assert os.path.exists("test_output.txt")
        
        with open("test_output.txt", "r") as f:
            content = f.read()
            assert content == "Hello, World!"

        # Clean up the file
        os.remove("test_output.txt")

        # Verify state manager interactions
        mock_state_manager.get_conversation_state.assert_called()
        mock_state_manager.update_conversation_state.assert_called()

        # Verify the generator yields a completion message
        assert any(res['type'] == 'implementation_complete' for res in results)