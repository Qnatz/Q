# tools/builtin_tools/stepwise_review_tool.py
"""
Stepwise Review Tool - Improved version
"""

import json
import time
import logging
import re
from typing import Dict, Any, List, Optional

from pydantic.dataclasses import PrivateAttr
from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType

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
                fixed_json = re.sub(r'(?<!\\)"(?=[^,}\]]*[,}\]])', '\\"', fixed_json)
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
2. Always escape quotes in strings as \\"
3. Use double quotes for all string keys and values
4. Do not include any text outside the JSON object
5. Ensure all braces and brackets are properly closed

{json_schema_hint}

Your response:"""
    
    return template.strip()


class StepwiseReviewTool(BaseTool):
    name: str = "Stepwise Review Tool"
    description: str = "Performs code review on implemented files."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

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
                    # Read the actual file content
                    file_content_result = self._llm.tool_impls['read_file'](absolute_path=fpath)
                    if file_content_result and "content" in file_content_result:
                        file_content = file_content_result['content']
                    else:
                        logger.warning(f"Could not read content for file: {fpath}. Using placeholder.")
                        file_content = f"Content of {fpath} (could not read actual content)"
                    
                    prompt = create_safe_prompt_template(
                        f"Review file: {fpath}",
                        f"File Content:\n{file_content}",
                        'Return JSON with format: {"rating": 1-10, "strengths": [...], "improvements": [...], "feedback": "..."}'
                    )
                    
                    if system_instruction:
                        prompt = f"System Instruction: {system_instruction}\n\n{prompt}"

                    llm_review_feedback = self._llm.generate_with_plan(
                        prompt,
                        system_instruction=system_instruction,
                        chunk_size=512,
                        step_size=256
                    )
                    
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
