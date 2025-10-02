# mcp_server.py

import inspect
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Since this is a standalone server, we need to import the necessary components
# from your existing codebase. We'll assume the current directory is the project root.
from tools.tool_registry import ToolRegistry
from tools.base_tool_classes import BaseTool
from memory.prompt_manager import PromptManager
from agent_processes.programming_module import ProgrammingModule

# --- MCP Data Models ---

class MCPToolParameter(BaseModel):
    name: str = Field(..., description="The name of the parameter.")
    type: str = Field(..., description="The data type of the parameter (e.g., 'string', 'integer', 'object').")
    description: str = Field(..., description="A description of what the parameter is for.")
    is_required: bool = Field(..., description="Whether the parameter is required.")

class MCPTool(BaseModel):
    name: str = Field(..., description="The name of the tool.")
    description: str = Field(..., description="A description of what the tool does.")
    parameters: List[MCPToolParameter] = Field(..., description="A list of parameters that the tool accepts.")

class MCPPrompt(BaseModel):
    name: str = Field(..., description="The name of the prompt.")
    content: str = Field(..., description="The content of the prompt template.")

class MCPLanguage(BaseModel):
    name: str = Field(..., description="The name of the language.")
    style_guide: str = Field(..., description="The style guide for the language.")
    testing_framework: str = Field(..., description="The testing framework for the language.")
    package_manager: str = Field(..., description="The package manager for the language.")
    guidance: str = Field(..., description="Language-specific guidance.")

class MCPResponse(BaseModel):
    """The top-level response from the MCP server."""
    tools: List[MCPTool] = Field(..., description="A list of tools available to the agent.")
    prompts: List[MCPPrompt] = Field(..., description="A list of prompt templates available to the agent.")
    languages: List[MCPLanguage] = Field(..., description="A list of supported languages and their configurations.")

# --- FastAPI Application ---

app = FastAPI(
    title="QAI Model Context Protocol (MCP) Server",
    description="Exposes tools, prompts, and other resources to AI agents via the MCP standard.",
    version="1.1.0",
)

# --- Helper Functions ---

def adapt_tool_to_mcp(tool: BaseTool) -> MCPTool:
    schema = tool.schema
    mcp_params = []
    if isinstance(schema.parameters, dict):
        for param_name, param_info in schema.parameters.items():
            mcp_params.append(
                MCPToolParameter(
                    name=param_name,
                    type=param_info.get("type", "string"),
                    description=param_info.get("description", ""),
                    is_required=param_name in schema.required,
                )
            )
    return MCPTool(
        name=schema.name,
        description=schema.description,
        parameters=mcp_params,
    )

# --- MCP Endpoint ---

@app.get("/mcp", response_model=MCPResponse, summary="Get Model Context")
def get_model_context():
    """
    Provides a list of available tools, prompts, and language configurations to an AI agent.
    """
    # This is a simplified instantiation for this standalone server.
    # In a real application, these would be shared instances.
    tool_registry = ToolRegistry()
    prompt_manager = PromptManager()
    # We need to instantiate the programming module to get its language configs.
    # This is a bit of a hack for this standalone server.
    programming_module = ProgrammingModule(llm_service=None, prompt_manager=prompt_manager, tool_registry=tool_registry)

    # 1. Adapt Tools
    mcp_tools = [adapt_tool_to_mcp(tool) for tool in tool_registry.tools.values()]

    # 2. Adapt Prompts
    all_prompts = prompt_manager.get_all_prompts()
    mcp_prompts = [
        MCPPrompt(name=name, content=prompt_manager.get_prompt(name))
        for name in all_prompts.get("ids", [])
    ]

    # 3. Adapt Languages
    mcp_languages = [
        MCPLanguage(name=lang, **config)
        for lang, config in programming_module.language_configs.items()
    ]

    return MCPResponse(
        tools=mcp_tools,
        prompts=mcp_prompts,
        languages=mcp_languages,
    )

# --- Root Endpoint for Health Check ---

@app.get("/", summary="Health Check")
def read_root():
    """A simple health check endpoint to confirm the server is running."""
    return {"status": "MCP server is running"}
