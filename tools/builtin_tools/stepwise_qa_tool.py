# tools/builtin_tools/stepwise_qa_tool.py
"""
Stepwise QA Tool - Improved version
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
                fixed_json = re.sub(r'(?<!\\)"(?=[^,}\\n]*[,}\\n])', '\\"', fixed_json)
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


class StepwiseQATool(BaseTool):
    name: str = "Stepwise QA Tool"
    description: str = "Performs quality assurance checks on implemented files based on a plan."

    def __init__(self, llm_service: Any, tool_registry: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self.llm_service = llm_service
        self.tool_registry = tool_registry

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_qa",
            description="Performs quality assurance checks on implemented files based on a plan.",
            parameters={
                "implemented_files": {"type": "array", "description": "List of paths to implemented files."},
                "plan": {"type": "object", "description": "The project plan, including declared files."},
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["implemented_files"],
            tool_type=ToolType.CODE_ANALYSIS,
            keywords=["qa", "test", "quality", "assurance", "check", "validate"],
            examples=[
                {"implemented_files": ["src/main.py"], "plan": {"files": [{"path": "src/main.py"}]}},
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
            plan = parameters.get("plan", {})
            system_instruction = parameters.get("system_instruction")

            if not implemented_files:
                return ToolResult(
                    status=ToolExecutionStatus.SUCCESS,
                    result={"qa_report": [], "overall_status": "NO_FILES"},
                    metadata={"files_checked": 0},
                    execution_time=time.time() - start_time
                )

            qa_report = []
            overall_status = "PASS"

            for fpath in implemented_files:
                try:
                    # FIX: Use file_operation tool instead of non-existent llm.tool_impls
                    file_content_result = self.tool_registry.execute_tool(
                        'file_operation',
                        parameters={
                            'operation': 'read',
                            'path': fpath
                        }
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
                    
                    llm_qa_feedback = self.llm_service.qa_code(file_content)
                    
                    # Parse QA response
                    qa_result = safe_json_parse(llm_qa_feedback, {
                        "status": "UNKNOWN", 
                        "issues": [], 
                        "feedback": llm_qa_feedback
                    })
                    
                    # Determine status
                    file_status = qa_result.get("status", "UNKNOWN")
                    if file_status not in ["PASS", "FAIL"]:
                        # Fallback: check for error keywords
                        feedback_lower = qa_result.get("feedback", "").lower()
                        file_status = "FAIL" if any(keyword in feedback_lower for keyword in ["error", "fail", "issue", "problem"]) else "PASS"
                    
                    if file_status == "FAIL":
                        overall_status = "FAIL"

                    qa_report.append({
                        "file": fpath,
                        "status": file_status,
                        "issues": qa_result.get("issues", []),
                        "feedback": qa_result.get("feedback", "No feedback provided")
                    })
                    
                except Exception as e:
                    logger.error(f"Error during QA for file {fpath}: {e}")
                    qa_report.append({
                        "file": fpath,
                        "status": "ERROR",
                        "issues": [f"QA process failed: {str(e)}"],
                        "feedback": f"Could not complete QA due to error: {str(e)}"
                    })
                    overall_status = "FAIL"
            
            execution_time = time.time() - start_time
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result={"qa_report": qa_report, "overall_status": overall_status},
                metadata={"files_checked": len(implemented_files)},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"QA process failed: {str(e)}",
                execution_time=time.time() - start_time
            )