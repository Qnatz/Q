# tools/builtin_tools/stepwise_review_tool.py
"""
Stepwise Review Tool - Improved version
"""

import json
import time
import logging
import re
from typing import Dict, Any, List, Optional

from pydantic import Field
from pydantic.dataclasses import dataclass, PrivateAttr
from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType
from core.llm_service import LLMService


logger = logging.getLogger(__name__)


def safe_json_parse(text: str, fallback_value: Any = None) -> Any:
    """Safely parse JSON with multiple fallback strategies"""
    
    # Strategy 1: Direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract JSON from markdown code blocks
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Extract JSON object pattern
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Strategy 4: Try to fix common JSON issues
            try:
                # Fix unescaped backslashes
                fixed_json = json_str.replace('\\', '\\\\')
                # Fix unescaped quotes in strings
                fixed_json = re.sub(r'(?<!\\)"(?=[^,}}\]]*[,}}\]])', '\\"', fixed_json)
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                pass
    
    # Strategy 5: Extract array pattern
    array_match = re.search(r'\[.*\]', text, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass
    
    logger.warning(f"Failed to parse JSON from text: {text[:200]}...")
    return fallback_value


def create_safe_prompt_template(base_prompt: str, context: str = "", 
                               json_schema_hint: str = "") -> str:
    """Create a prompt that encourages proper JSON formatting"""
    
    template = f"""
{base_prompt}

{context}

IMPORTANT: Your response must be valid JSON. Follow these rules:
1. Always escape backslashes as \\\\ 
2. Always escape quotes in strings as \""
3. Use double quotes for all string keys and values
4. Do not include any text outside the JSON object
5. Ensure all braces and brackets are properly closed

{json_schema_hint}

Your response:"""
    
    return template.strip()


class StepwiseReviewTool(BaseTool):
    name: str = "Stepwise Review Tool"
    description: str = "Performs code review on implemented files."

    def __init__(self, llm_service: Any, tool_registry: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self.llm_service = llm_service
        self.tool_registry = tool_registry

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_review",
            description="Performs code review on implemented files.",
            parameters={
                "implemented_files": {"type": "array", "description": "List of paths to implemented files."},
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["implemented_files"],
            tool_type=ToolType.CODE_ANALYSIS,
            keywords=["review", "code", "feedback", "critique", "quality"],
            examples=[
                {"implemented_files": ["src/utils.py"]},
            ]
        )

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            implemented_files = parameters["implemented_files"]
            system_instruction = parameters.get("system_instruction")

            if not implemented_files:
                return ToolResult(
                    status=ToolExecutionStatus.SUCCESS,
                    result={"review_report": []},
                    metadata={"files_reviewed": 0},
                    execution_time=time.time() - start_time
                )

            review_report = []

            for fpath in implemented_files:
                try:
                    file_content_result = self.tool_registry.execute_tool(
                        'file_operation',
                        parameters={
                            'operation': 'read', 
                            'path': fpath
                        },
                        context=context # Pass the context
                    )
                    
                    # FIX: Handle ToolResult properly
                    if (file_content_result and 
                        file_content_result.status == ToolExecutionStatus.SUCCESS and 
                        file_content_result.result and 
                        'content' in file_content_result.result):
                        file_content = file_content_result.result['content']
                    else:
                        logger.warning(f"Could not read content for file: {fpath}. Using placeholder.")
                        file_content = f"Content of {fpath} (could not read actual content)"
                    
                    llm_review_feedback = self.llm_service.review_code(file_content)
                    
                    # Parse review response
                    review_result = safe_json_parse(llm_review_feedback, {
                        "rating": 5,
                        "strengths": [],
                        "improvements": [],
                        "feedback": llm_review_feedback
                    })
                    
                    review_report.append({
                        "file": fpath,
                        "rating": review_result.get("rating", 5),
                        "strengths": review_result.get("strengths", []),
                        "improvements": review_result.get("improvements", []),
                        "feedback": review_result.get("feedback", "No feedback provided")
                    })
                    
                except Exception as e:
                    logger.error(f"Error during review for file {fpath}: {e}")
                    review_report.append({
                        "file": fpath,
                        "rating": 0,
                        "strengths": [],
                        "improvements": [f"Review process failed: {str(e)}"],
                        "feedback": f"Could not complete review due to error: {str(e)}"
                    })
            
            execution_time = time.time() - start_time
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result={"review_report": review_report},
                metadata={"files_reviewed": len(implemented_files)},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Review process failed: {str(e)}",
                execution_time=time.time() - start_time
            )