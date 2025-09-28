# tools/builtin_tools/stepwise_tools.py
"""
Stepwise tools (planner, implementation, QA, review) - Improved version
"""

import json
import time
import logging
import re
from typing import Dict, Any, List, Optional

from pydantic.dataclasses import PrivateAttr
from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType
from tools.utils.validation_utils import SchemaValidatorTool
from schemas.implementation_schema import IMPLEMENTATION_SCHEMA

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
                    f"Based on the following project description, what are the main components or sections of this project?",
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


class StepwiseImplementationTool(BaseTool):
    name: str = "Stepwise Implementation Tool"
    description: str = "Implements tasks one by one from a provided list of tasks."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_implementation",
            description="Implements tasks one by one from a provided list of tasks.",
            parameters={
                "tasks": {"type": "array", "description": "List of tasks to implement."}, 
                "project_title": {"type": "string", "description": "The title of the project."}, 
                "system_instruction": {"type": "string", "description": "Optional system instructions for the LLM.", "default": None}
            },
            required=["tasks"],
            tool_type=ToolType.IMPLEMENTATION,
            keywords=["implement", "task", "stepwise", "code", "develop"],
            examples=[
                {"tasks": [{"task": "Create a user authentication module.", "description": "Implement login and registration."}], "system_instruction": "Use PostgreSQL."}, 
                {"tasks": [{"task": "Design database schema.", "description": "Define tables for users and products."}], "system_instruction": "Use PostgreSQL."} 
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
            
            tasks = parameters["tasks"]
            project_title = parameters.get("project_title", "Untitled Project")
            system_instruction = parameters.get("system_instruction")
            
            all_outputs = []
            implementation_summary = ""
            successful_tasks = 0
            failed_tasks = 0
            
            for idx, task in enumerate(tasks, start=1):
                task_name = task.get('task', f'Task {idx}')
                task_desc = task.get('description', 'No description')
                
                retries = 3
                task_success = False
                
                for attempt in range(retries):
                    try:
                        prompt = create_safe_prompt_template(
                            f"Implement task {idx}: {task_name}",
                            f"Description: {task_desc}\nSummary of previously implemented tasks:\n{implementation_summary}" if implementation_summary else f"Description: {task_desc}",
                            'Return JSON with format: {"files": [{"file_path": "...", "action": "create" | "update" | "delete", "content": "..."}]}'
                        )
                        
                        if system_instruction:
                            prompt = f"System Instruction: {system_instruction}\n\n{prompt}"
                        
                        chunk_output = self._llm.generate_with_plan(
                            prompt,
                            system_instruction=system_instruction,
                            chunk_size=512,
                            step_size=256
                        )
                        
                        # Parse the JSON response safely
                        chunk_json = safe_json_parse(chunk_output, {"files": []})
                        
                        # Validate the structure
                        if not isinstance(chunk_json, dict) or "files" not in chunk_json:
                            chunk_json = {"files": []}
                        
                        # Ensure files is a list
                        if not isinstance(chunk_json["files"], list):
                            chunk_json["files"] = []

                        # Validate the chunk against the implementation schema
                        try:
                            if not SchemaValidatorTool()._run(json.dumps(chunk_json['files']), 'implementation'):
                                logger.warning(f"Schema validation failed for task {task_name}")
                                # Continue with the task but log the validation failure
                        except Exception as e:
                            logger.warning(f"Schema validation failed for task {task_name}: {e}")
                        
                        all_outputs.append(chunk_json)
                        implementation_summary = self.summarize_implementation(all_outputs)
                        task_success = True
                        successful_tasks += 1
                        
                        logger.info(f"Successfully implemented task: {task_name}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        logger.error(f"Error implementing task {task_name} (attempt {attempt + 1}/{retries}): {e}")
                        if attempt + 1 == retries:
                            # Final attempt failed
                            failed_tasks += 1
                            # Add empty result to maintain task order
                            all_outputs.append({"files": [], "error": str(e), "task": task_name})
                        else:
                            time.sleep(1)  # Wait before retrying
                
                if not task_success:
                    logger.error(f"Failed to implement task after {retries} attempts: {task_name}")
            
            execution_time = time.time() - start_time
            
            # Determine overall status
            if successful_tasks == 0:
                status = ToolExecutionStatus.ERROR
                error_message = f"All {len(tasks)} tasks failed to implement"
            elif failed_tasks > 0:
                status = ToolExecutionStatus.ERROR
                error_message = f"{failed_tasks} out of {len(tasks)} tasks failed to implement"
            else:
                status = ToolExecutionStatus.SUCCESS
                error_message = None

            all_files = []
            for output in all_outputs:
                all_files.extend(output.get("files", []))

            return ToolResult(
                status=status,
                result=all_files,
                metadata={
                    "tasks_count": len(tasks),
                    "successful_tasks": successful_tasks,
                    "failed_tasks": failed_tasks
                },
                execution_time=execution_time,
                error_message=error_message
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=f"Implementation failed: {str(e)}",
                execution_time=time.time() - start_time
            )

    def summarize_implementation(self, all_outputs: list) -> str:
        """Summarize implemented outputs"""
        summary = "Completed Implementations:\n"
        for output in all_outputs:
            if "error" in output:
                summary += f"- Task '{output.get('task', 'Unknown')}': FAILED ({output['error']})\n"
            else:
                for file_impl in output.get("files", []):
                    file_path = file_impl.get('file_path', 'Unknown file')
                    action = file_impl.get('action', 'unknown')
                    summary += f"- File: {file_path}, Action: {action}\n"
        return summary


class StepwiseQATool(BaseTool):
    name: str = "Stepwise QA Tool"
    description: str = "Performs quality assurance checks on implemented files based on a plan."
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm

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
                    # Try to read the file content (placeholder implementation)
                    file_content = f"Content of {fpath} (placeholder)"
                    
                    prompt = create_safe_prompt_template(
                        f"Perform QA on file: {fpath}",
                        f"File Content:\n{file_content}\n\nPlan details: {json.dumps(plan, indent=2)}",
                        'Return JSON with format: {"status": "PASS/FAIL", "issues": [...], "feedback": "..."}'
                    )
                    
                    if system_instruction:
                        prompt = f"System Instruction: {system_instruction}\n\n{prompt}"

                    llm_qa_feedback = self._llm.generate_with_plan(
                        prompt,
                        system_instruction=system_instruction,
                        chunk_size=512,
                        step_size=256
                    )
                    
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
                    # Try to read the file content (placeholder implementation)
                    file_content = f"Content of {fpath} (placeholder)"
                    
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
