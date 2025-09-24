# planning_module.py
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

from qllm.unified_llm import UnifiedLLM
from schemas.plan_schema import PLAN_SCHEMA
from utils.json_utils import safe_json_extract
from utils.validation_utils import validate
from memory.prompt_manager import PromptManager
from tools.tool_registry import ToolRegistry, ToolExecutionStatus

logger = logging.getLogger(__name__)

@dataclass
class PlanningResult:
    success: bool
    plan: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None

class PlanningModule:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager, tool_registry: ToolRegistry):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.tool_registry = tool_registry
        self.logger = logging.getLogger(__name__)
        self._fallback_prompt_name = "orchestrator_planning_phase_prompt.md"

    def plan(self, user_request: str, refine: bool = False, errors: Optional[str] = None) -> str:
        """Generate project plan using stepwise planner with fallback"""
        self.logger.info(f"Generating plan for request: {user_request[:100]}...")
        
        # Try stepwise planner first
        plan_result = self._execute_stepwise_planner(user_request, refine, errors)
        if plan_result.success and plan_result.plan:
            return json.dumps(plan_result.plan)
        
        # Fallback to LLM-based planning
        self.logger.warning("Stepwise planner failed, using LLM fallback")
        fallback_result = self._fallback_planning(user_request, refine, errors)
        if fallback_result.success and fallback_result.plan:
            return json.dumps(fallback_result.plan)
        
        # Ultimate fallback
        error_msg = plan_result.error or fallback_result.error or "Unknown planning error"
        return json.dumps({"error": f"Planning failed: {error_msg}"})

    def _execute_stepwise_planner(self, user_request: str, refine: bool, errors: Optional[str]) -> PlanningResult:
        """Execute stepwise planner tool"""
        try:
            parameters = {"refined_prompt": user_request}
            if refine:
                parameters["refine"] = True
            if errors:
                parameters["previous_errors"] = errors
            
            plan_result = self.tool_registry.execute_tool("stepwise_planner", parameters)
            
            if plan_result.status == ToolExecutionStatus.SUCCESS:
                plan_data = plan_result.result
                if self._validate_plan(plan_data):
                    return PlanningResult(success=True, plan=plan_data)
                else:
                    return PlanningResult(success=False, error="Invalid plan structure from tool")
            else:
                return PlanningResult(success=False, error=plan_result.error_message)
                
        except Exception as e:
            self.logger.error(f"Stepwise planner execution failed: {e}")
            return PlanningResult(success=False, error=str(e))

    def _fallback_planning(self, user_request: str, refine: bool, errors: Optional[str]) -> PlanningResult:
        """Fallback planning using LLM when tool fails"""
        try:
            system_prompt = self.prompt_manager.get_prompt(self._fallback_prompt_name)
            if not system_prompt:
                return PlanningResult(success=False, error="Fallback prompt not available")
            
            messages = [{"role": "system", "content": system_prompt}]
            
            user_content = f"User request: {user_request}"
            if refine:
                user_content += "\nThis is a refinement request."
            if errors:
                user_content += f"\nPrevious errors to address: {errors}"
            
            messages.append({"role": "user", "content": user_content})
            
            response = self.llm.generate(messages, use_tools=False)
            plan_data = safe_json_extract(response)
            
            if plan_data and self._validate_plan(plan_data):
                return PlanningResult(success=True, plan=plan_data)
            else:
                return PlanningResult(success=False, error="Invalid plan from LLM fallback")
                
        except Exception as e:
            self.logger.error(f"Fallback planning failed: {e}")
            return PlanningResult(success=False, error=str(e))

    def _validate_plan(self, plan_data: Dict[str, Any]) -> bool:
        """Validate plan against schema"""
        try:
            return validate(plan_data, PLAN_SCHEMA)
        except Exception as e:
            self.logger.warning(f"Plan validation failed: {e}")
            # Basic structural validation as fallback
            required_keys = {"tasks", "description", "requirements"}
            return all(key in plan_data for key in required_keys)