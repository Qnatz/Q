import json
import re
from typing import Dict, Any, List, Optional

from qllm.unified_llm import UnifiedLLM
from memory.prompt_manager import PromptManager
from schemas.plan_schema import PLAN_SCHEMA
from utils.json_utils import safe_json_extract
from utils.validation_utils import validate
import logging

logger = logging.getLogger(__name__)


def forgiving_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """More forgiving JSON extractor that attempts to recover the largest JSON block."""
    try:
        # Try the normal extractor first
        plan = safe_json_extract(text)
        if plan:
            return plan

        # Fallback: regex to grab first {...} block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        logger.error(f"Forgiving JSON extraction failed: {e}")
    return None


class PlanningModule:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self._max_retries = 3

    def generate_plan(
        self,
        project_title: str,
        user_request: str,
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Generate a detailed plan for the user's request."""
        logger.info(f"Generating plan for request: {user_request[:100]}...")

        # Try stepwise planning first
        stepwise_plan = self._stepwise_planning(project_title, user_request, conversation_history)
        if stepwise_plan:
            return stepwise_plan

        logger.warning("Stepwise planner failed, using LLM fallback")
        # Fallback to direct LLM planning
        return self._llm_fallback_planning(project_title, user_request, conversation_history)

    def _stepwise_planning(
        self,
        project_title: str,
        user_request: str,
        conversation_history: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        system_prompt = self.prompt_manager.get_prompt("orchestrator/plan_generation")
        if not system_prompt:
            logger.error("Orchestrator planning phase prompt not found.")
            return None

        # Extract just the template content if it's wrapped in variable assignment
        if system_prompt.startswith('PLAN_GENERATION_PROMPT = """'):
            lines = system_prompt.split('\n')
            system_prompt = '\n'.join(lines[1:-1])

        formatted_system_prompt = system_prompt.format(
            PROJECT_TITLE=project_title,
            REFINED_PROMPT=user_request,
            USER_REQUEST_PROMPT=user_request,
            FOLLOWUP_MESSAGE_PROMPT="",
            GITHUB_WORKFLOWS_PERMISSIONS_PROMPT="",
            CUSTOM_RULES="",
            SCRATCHPAD="",
            PLAN_SCHEMA=json.dumps(PLAN_SCHEMA, indent=2),  # ✅ Inject schema
        )

        messages = [
            {"role": "system", "content": formatted_system_prompt},
            *conversation_history,
            {"role": "user", "content": user_request},
        ]

        for attempt in range(self._max_retries):
            try:
                response_text = self.llm.generate(messages, use_tools=False)
                logger.info(f"LLM Raw Response: {response_text}")
                plan = forgiving_json_extract(response_text)
                logger.info(f"Extracted Plan: {plan}")

                if plan:
                    if validate(plan, PLAN_SCHEMA):
                        return plan
                    else:
                        logger.warning("Plan failed schema validation but will be returned as-is")
                        return plan
            except Exception as e:
                logger.error(f"Stepwise planner execution failed: {e}")
                continue
        return None

    def _llm_fallback_planning(
        self,
        project_title: str,
        user_request: str,
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Generate a plan directly using the LLM as a fallback."""
        system_prompt = self.prompt_manager.get_prompt("orchestrator_planning_phase_prompt")
        if not system_prompt:
            logger.error("Orchestrator planning phase prompt not found for fallback.")
            return self._create_minimal_plan(project_title, user_request)

        formatted_system_prompt = system_prompt.format(
            FOLLOWUP_MESSAGE_PROMPT="",
            USER_REQUEST_PROMPT=user_request,
            GITHUB_WORKFLOWS_PERMISSIONS_PROMPT="",
            SCRATCHPAD="",
            PLAN_SCHEMA=json.dumps(PLAN_SCHEMA, indent=2),  # ✅ Inject schema
        )

        messages = [
            {"role": "system", "content": formatted_system_prompt},
            *conversation_history,
            {"role": "user", "content": user_request},
        ]

        for attempt in range(self._max_retries):
            try:
                response_text = self.llm.generate(messages, use_tools=False)
                logger.info(f"LLM Raw Response (fallback): {response_text}")
                plan = forgiving_json_extract(response_text)
                logger.info(f"Extracted Plan (fallback): {plan}")

                if plan:
                    if validate(plan, PLAN_SCHEMA):
                        return plan
                    else:
                        logger.warning("Fallback plan failed validation but will be returned as-is")
                        return plan
            except Exception as e:
                logger.error(f"Fallback planning failed: {e}")
                continue

        logger.error("All planning attempts failed, returning minimal plan")
        return self._create_minimal_plan(project_title, user_request)

    def _create_minimal_plan(self, project_title: str, user_request: str) -> Dict[str, Any]:
        """Create a minimal valid plan structure when all else fails."""
        return {
            "project": {
                "name": project_title,
                "description": user_request,
            },
            "files": [],
            "tasks": [
                {
                    "task": "Implement based on user request",
                    "description": f"Implement: {user_request}",
                    "module": "ProgrammingModule",
                    "output": "Working implementation",
                }
            ],
        }

    def validate_plan(self, plan: Dict[str, Any]) -> bool:
        """Validate the structure and content of the generated plan."""
        try:
            return validate(plan, PLAN_SCHEMA)
        except Exception as e:
            logger.warning(f"Plan validation failed: {e}")
            return False
