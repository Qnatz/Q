# tools/builtin_tools/stepwise_planner_tool.py
"""
Stepwise Planner Tool - Improved version
"""

import json
import time
import logging
import re
from typing import Dict, Any, List, Optional

from pydantic.dataclasses import PrivateAttr
from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType
from tools.utils.validation_utils import SchemaValidatorTool

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


class StepwisePlannerTool(BaseTool):
    name: str = "Stepwise Planner Tool"
    description: str = "Generates a stepwise project plan for a given prompt, breaking it down by sections."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_planner",
            description="Generates a stepwise project plan for a given prompt, breaking it down by sections.",
            parameters={
                "refined_prompt": {"type": "string", "description": "The refined prompt for which to generate a plan."},
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["refined_prompt"],
            tool_type=ToolType.PLANNING,
            keywords=["plan", "project", "stepwise", "breakdown", "sections"],
            examples=[
                {"refined_prompt": "Develop a simple e-commerce website.", "system_instruction": "Focus on scalability."}
            ]
        )

    def _generate_sections(self, refined_prompt: str) -> List[str]:
        """Generate project sections with improved error handling"""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates a list of components for a software project. Always respond with valid JSON."
            },
            {
                "role": "user",
                "content": create_safe_prompt_template(
                    "Based on the following project description, what are the main components or sections of this project?",
                    f"Project Description: {refined_prompt}",
                    'Return a JSON array of strings like: ["Frontend (UI/UX)", "Backend (API)", "Database", "Authentication", "Deployment"]'
                )
            }
        ]
        
        try:
            response = self._llm.generate(messages, use_tools=False)
            sections = safe_json_parse(response, [])
            
            if isinstance(sections, list) and all(isinstance(s, str) for s in sections):
                return sections
        except Exception as e:
            logger.warning(f"Failed to generate sections: {e}")

        # Fallback to default sections
        return ["UI/UX", "Backend", "Database", "API", "Integration"]

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        start_time = time.time()
        
        try:
            if not self.validate_parameters(parameters):
                return ToolResult(
                    status=ToolExecutionStatus.VALIDATION_ERROR,
                    result=None,
                    error_message="Parameter validation failed"
                )
            
            refined_prompt = parameters["refined_prompt"]
            system_instruction = parameters.get("system_instruction")
            
            sections = self._generate_sections(refined_prompt)
            final_plan = {"project": {"name": "", "description": ""}, "files": [], "tasks": []}
            plan_summary = ""
            
            for section in sections:
                try:
                    prompt = create_safe_prompt_template(
                        f"Generate the {section} section of the project plan for: {refined_prompt}",
                        f"Summary of previously generated sections:\n{plan_summary}" if plan_summary else "",
                        'Return JSON with format: {"tasks": [...], "files": [...]}'
                    )
                    
                    if system_instruction:
                        prompt = f"System Instruction: {system_instruction}\n\n{prompt}"
                    
                    chunk_output = self._llm.generate_with_plan(
                        prompt,
                        system_instruction=system_instruction,
                        chunk_size=512,
                        step_size=256
                    )
                    
                    chunk_json = safe_json_parse(chunk_output, {"tasks": [], "files": []})
                    
                    # Validate the chunk
                    try:
                        SchemaValidatorTool()._run(json.dumps(chunk_json), 'plan')
                    except Exception as e:
                        logger.warning(f"Schema validation failed for {section}: {e}")
                        continue
                    
                    # Merge results
                    final_plan["tasks"].extend(chunk_json.get("tasks", []))
                    final_plan["files"].extend(chunk_json.get("files", []))
                    
                    plan_summary = self.summarize_plan(final_plan)
                    
                except Exception as e:
                    logger.error(f"Error processing section {section}: {e}")
                    continue
            
            # Final validation
            try:
                SchemaValidatorTool()._run(json.dumps(final_plan), 'plan')
            except Exception as e:
                logger.warning(f"Final plan validation failed: {e}")
            
            execution_time = time.time() - start_time
            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=final_plan,
                metadata={"refined_prompt": refined_prompt},
                execution_time=execution_time
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Planning failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    def summarize_plan(self, current_plan: dict) -> str:
        """Summarize current plan state"""
        summary = "Completed Implementations:\n" + "\n".join(
            [f"- {f.get('file_path', 'Unknown file')}" for f in current_plan.get("files", [])]
        )
        summary += "\n\nGenerated Tasks:\n" + "\n".join(
            [f"- {t.get('task', 'Unknown task')}" for t in current_plan.get("tasks", [])]
        )
        return summary
