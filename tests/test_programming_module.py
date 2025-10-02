import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch

from agent_processes.programming_module import ProgrammingModule, BuildSystem

@pytest.fixture
def mock_llm_service():
    return MagicMock()

@pytest.fixture
def mock_prompt_manager():
    return MagicMock()

@pytest.fixture
def mock_tool_registry():
    return MagicMock()

def test_programming_module_initialization(mock_llm_service, mock_prompt_manager, mock_tool_registry):
    """Test that the ProgrammingModule initializes correctly."""
    module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry)
    assert module is not None

@patch("glob.glob", return_value=["pom.xml"])
def test_detect_build_system_maven(mock_glob, mock_llm_service, mock_prompt_manager, mock_tool_registry):
    """Test that the _detect_build_system method correctly identifies Maven."""
    module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry)
    build_system = module._detect_build_system()
    assert build_system == BuildSystem.MAVEN

def test_detect_language_from_context(mock_llm_service, mock_prompt_manager, mock_tool_registry):
    """Test that the _detect_language_from_context method correctly calls the LLM and returns the language."""
    module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry)
    mock_llm_service.generate.return_value = "python"
    language = module._detect_language_from_context("My Project", {"tasks": [{"description": "Create a web server"}]})
    assert language == "python"
    mock_llm_service.generate.assert_called_once()

def test_get_build_commands(mock_llm_service, mock_prompt_manager, mock_tool_registry):
    """Test that the _get_build_commands method returns the correct commands for a given build system."""
    module = ProgrammingModule(mock_llm_service, mock_prompt_manager, mock_tool_registry)
    maven_commands = module._get_build_commands(BuildSystem.MAVEN)
    assert maven_commands["build_command"] == ["./mvnw", "compile"] if os.path.exists("./mvnw") else ["mvn", "compile"]
