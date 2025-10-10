import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_processes.programming_module import ProgrammingModule

@pytest.fixture
def mock_llm_service():
    return MagicMock()

@pytest.fixture
def mock_prompt_manager():
    return MagicMock()

@pytest.fixture
def mock_tool_registry():
    return MagicMock()

@pytest.fixture
def mock_state_manager():
    """Fixture for a mock state manager."""
    return MagicMock()

def test_programming_module_initialization(mock_llm_service, mock_prompt_manager, mock_tool_registry, mock_state_manager):
    """Test that the ProgrammingModule initializes correctly."""
    module = ProgrammingModule(
        llm_service=mock_llm_service,
        prompt_manager=mock_prompt_manager,
        tool_registry=mock_tool_registry,
        state_manager=mock_state_manager
    )
    assert module is not None

@patch("agent_processes.programming_module.ProgrammingModule._get_current_files")
def test_implement_with_no_tasks(mock_get_files, mock_llm_service, mock_prompt_manager, mock_tool_registry, mock_state_manager):
    """Test that the implement method handles a plan with no tasks."""
    module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry, mock_state_manager)

    plan = {"tasks": []}
    project_title = "Test Project"
    user_id = "test_user"
    project_id = "test_project"

    # The implement method is a generator. We need to consume it.
    results = list(module.implement(plan, project_title, user_id, project_id))

    assert len(results) == 1
    assert results[0]["type"] == "complete"
    assert results[0]["status"] == "success"
    assert "No tasks to implement" in results[0]["message"]