# mcp_server.py
import inspect
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Import the actual LLMService and other necessary components
from core.llm_service import LLMService
from tools.tool_registry import ToolRegistry
from tools.base_tool_classes import BaseTool
from qllm.unified_llm import UnifiedLLM
from qllm.config import Config
from memory.prompt_manager import PromptManager
from agent_processes.programming_module import ProgrammingModule

# --- Placeholder Dependencies ---
# We need a placeholder for UnifiedMemory for the PromptManager
class MockUnifiedMemory:
    def get_prompt(self, name: str) -> Optional[str]:
        return f"Prompt for {name}"

    def get_all_prompts(self) -> Dict[str, Any]:
        return {"ids": ["code_assistance", "code_review", "code_qa"]}

# --- Data Models ---

class CodeInput(BaseModel):
    code: str = Field(..., description="The code to be processed.")

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
    tools: List[MCPTool] = Field(..., description="A list of tools available to the agent.")
    prompts: List[MCPPrompt] = Field(..., description="A list of prompt templates available to the agent.")
    languages: List[MCPLanguage] = Field(..., description="A list of supported languages and their configurations.")

# --- FastAPI Application ---

app = FastAPI(
    title="QAI Model Context Protocol (MCP) Server",
    description="Exposes tools, prompts, and other resources to AI agents via the MCP standard.",
    version="1.4.0",
)

# --- Service Instantiation ---
# Correctly instantiate the services with the necessary configurations.
config = Config(backend="http") # Use a backend that doesn't require API keys for this server
unified_llm = UnifiedLLM(cfg=config)
prompt_manager = PromptManager(unified_memory=MockUnifiedMemory())
llm_service = LLMService(llm=unified_llm, prompt_manager=prompt_manager)
tool_registry = ToolRegistry(llm=unified_llm)
programming_module = ProgrammingModule(llm_service=llm_service, prompt_manager=prompt_manager, tool_registry=tool_registry)


# --- Helper Functions ---

def adapt_tool_to_mcp(tool: BaseTool) -> MCPTool:
    schema = tool.schema
    mcp_params = []
    if hasattr(schema, 'parameters') and isinstance(schema.parameters, dict):
        for param_name, param_info in schema.parameters.items():
            mcp_params.append(
                MCPToolParameter(
                    name=param_name,
                    type=param_info.get("type", "string"),
                    description=param_info.get("description", ""),
                    is_required=param_name in getattr(schema, 'required', []),
                )
            )
    return MCPTool(
        name=schema.name,
        description=schema.description,
        parameters=mcp_params,
    )

# --- Endpoints ---

@app.get("/", summary="Health Check")
def read_root():
    return {"status": "MCP server is running"}

@app.get("/mcp", response_model=MCPResponse, summary="Get Model Context")
def get_model_context():
    """Provides a list of available tools, prompts, and language configurations."""
    mcp_tools = [adapt_tool_to_mcp(tool) for tool in tool_registry.tools.values()]
    all_prompts = prompt_manager.get_all_prompts()
    mcp_prompts = [
        MCPPrompt(name=name, content=prompt_manager.get_prompt(name))
        for name in all_prompts.get("ids", [])
    ]
    mcp_languages = [
        MCPLanguage(
            name=lang,
            style_guide=config.get('style_guide', 'N/A'),
            testing_framework=config.get('testing_framework', 'N/A'),
            package_manager=config.get('package_manager', 'N/A'),
            guidance=f"Guidance for {lang}"
        )
        for lang, config in llm_service.language_configs.items()
    ]
    return MCPResponse(tools=mcp_tools, prompts=mcp_prompts, languages=mcp_languages)

@app.post("/assist", summary="Get Code Assistance")
def get_assistance(code_input: CodeInput):
    """Provides code assistance on the given code by explaining it."""
    try:
        # Use the existing explain_code method from LLMService
        assistance = llm_service.explain_code(code_input.code)
        return {"assistance": assistance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review", summary="Get Code Review")
def get_review(code_input: CodeInput):
    """Provides a code review on the given code."""
    try:
        review = llm_service.review_code(code_input.code)
        return {"review": review}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/qa", summary="Get Code QA")
def get_qa(code_input: CodeInput):
    """Provides a QA on the given code."""
    try:
        qa_feedback = llm_service.qa_code(code_input.code)
        return {"qa": qa_feedback}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))