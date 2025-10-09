import json
import re
import logging
from typing import Dict, Any, List, Optional

import time

from core.llm_service import LLMService
from memory.prompt_manager import PromptManager
from schemas.plan_schema import PLAN_SCHEMA
from utils.json_utils import safe_json_extract
from utils.validation_utils import validate_plan
from core.project_context import ProjectContext  # <-- new

logger = logging.getLogger(__name__)

PROMPT_MAPPINGS = {
    # Only the planning prompt is used
    "orchestrator/plan_generation": "orchestrator_planning_phase_prompt"
}


def forgiving_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """More forgiving JSON extractor that attempts to recover the largest JSON block."""
    try:
        plan = safe_json_extract(text)
        if plan:
            return plan
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        logger.error(f"Forgiving JSON extraction failed: {e}")
    return None


class PlanningModule:
    def __init__(
        self,
        llm_service: LLMService,
        prompt_manager: PromptManager,
        project_context: ProjectContext
    ):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.project_context = project_context
        self._max_retries = 3

    def _generate_project_title(self, idea: str) -> str:
        """Generates a creative and descriptive project name with a timestamp."""
        try:
            prompt = f"Generate a short, creative, and descriptive project name (2-3 words, snake_case) for the following idea. Examples: 'android_app', 'finance_tracker', 'galaxy_explorer'.\n\nIdea: \"{idea}\"\n\nName:"
            system_instruction = "You are a creative naming expert. Provide only the name."
            
            name_suggestion = self.llm_service.llm.generate(
                [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
                use_tools=False
            ).strip().lower().replace(" ", "_").replace("-", "_")
            
            # Basic validation
            if not re.match(r"^[a-z0-9_]+$", name_suggestion) or len(name_suggestion) > 50:
                 # Fallback to simpler logic if LLM fails or gives bad output
                 name_suggestion = "_".join(idea.split()[:3]).lower()

        except Exception as e:
            self.logger.error(f"Error generating project title with LLM: {e}")
            # Fallback to simpler logic
            name_suggestion = "_".join(idea.split()[:3]).lower()

        timestamp = int(time.time())
        return f"{name_suggestion}_{timestamp}"

    def _load_prompt(self, prompt_name: str) -> str:
        mapped_name = PROMPT_MAPPINGS.get(prompt_name, prompt_name)
        prompt_content = self.prompt_manager.get_prompt(mapped_name)
        if not prompt_content:
            logger.warning(f"Prompt {prompt_name} not found, using fallback")
            return self._get_fallback_prompt(prompt_name)
        return prompt_content

    def _get_fallback_prompt(self, prompt_name: str) -> str:
        logger.error(f"No specific fallback prompt for {prompt_name}. Returning generic planning prompt.")
        return (
            "You are an AI assistant specialized in software project planning. "
            "Generate a detailed plan in JSON format based on the user's request."
        )

    def generate_plan(
        self,
        refined_prompt: str,
        conversation_history: List[Dict[str, str]],
        project_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a detailed plan using project-specific context."""
        if not project_title:
            project_title = self._generate_project_title(refined_prompt)

        logger.info(f"Generating plan for project {project_title} with request: {refined_prompt[:100]}...")

        # Stepwise planning
        stepwise_plan = self._stepwise_planning(project_title, refined_prompt, conversation_history)
        if stepwise_plan:
            return stepwise_plan

        # Fallback to direct LLM planning
        logger.warning("Stepwise planner failed, using LLM fallback")
        return self._llm_fallback_planning(project_title, refined_prompt, conversation_history)

    def _stepwise_planning(
        self,
        project_title: str,
        refined_prompt: str,
        conversation_history: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        system_prompt = self._load_prompt("orchestrator_planning_phase_prompt")

        # Unwind triple quotes if present
        if system_prompt.startswith('PLAN_GENERATION_PROMPT = ""'):
            lines = system_prompt.split('\n')
            system_prompt = '\n'.join(lines[1:-1])

        # Dump schema as readable JSON
        schema_str = json.dumps(PLAN_SCHEMA, indent=2, ensure_ascii=False)

        logger.debug("--- STEPWISE PLANNING DEBUG ---")
        logger.debug(f"Project Title: {project_title}")
        logger.debug(f"Refined Prompt: {refined_prompt}")
        # logger.debug(f"System Prompt (before format):\n{system_prompt}")
        logger.debug("--- END DEBUG ---")

        try:
            formatted_system_prompt = system_prompt.format(
                PROJECT_TITLE=project_title,
                REFINED_PROMPT=refined_prompt,
                USER_REQUEST_PROMPT=refined_prompt,
                FOLLOWUP_MESSAGE_PROMPT="",
                GITHUB_WORKFLOWS_PERMISSIONS_PROMPT="",
                SCRATCHPAD="",
                PLAN_SCHEMA=schema_str,
            )
        except KeyError as e:
            logger.error(f"KeyError during prompt formatting: {e}")
        messages = [
            {"role": "system", "content": formatted_system_prompt},
            *conversation_history,
            {"role": "user", "content": refined_prompt},
        ]

        for attempt in range(self._max_retries):
            try:
                response_text = self.llm_service.llm.generate(messages, use_tools=False)
                logger.info(f"LLM RESPONSE:\n{response_text}")
                plan = forgiving_json_extract(response_text)
                if plan and self.validate_plan(plan):
                    return plan
            except Exception as e:
                logger.error(f"Stepwise planner attempt {attempt+1} failed: {e}")
                continue
        return None

    def _llm_fallback_planning(
        self,
        project_title: str,
        refined_prompt: str,
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        system_prompt = self._load_prompt("orchestrator_planning_phase_prompt")
        if not system_prompt:
            logger.error("Fallback prompt not found.")
            return self._create_minimal_plan(project_title, refined_prompt)

        # Dump schema as readable JSON
        schema_str = json.dumps(PLAN_SCHEMA, indent=2, ensure_ascii=False)

        formatted_system_prompt = system_prompt.format(
            PROJECT_TITLE=project_title,
            REFINED_PROMPT=refined_prompt,
            FOLLOWUP_MESSAGE_PROMPT="",
            USER_REQUEST_PROMPT=refined_prompt,
            GITHUB_WORKFLOWS_PERMISSIONS_PROMPT="",
            SCRATCHPAD="",
            PLAN_SCHEMA=schema_str,
        )

        messages = [
            {"role": "system", "content": formatted_system_prompt},
            *conversation_history,
            {"role": "user", "content": refined_prompt},
        ]

        for attempt in range(self._max_retries):
            try:
                response_text = self.llm_service.llm.generate(messages, use_tools=False)
                plan = forgiving_json_extract(response_text)
                if plan and self.validate_plan(plan):
                    return plan
            except Exception as e:
                logger.error(f"Fallback planning attempt {attempt+1} failed: {e}")
                continue
        return self._create_minimal_plan(project_title, refined_prompt)

    def _create_minimal_plan(self, project_title: str, refined_prompt: str) -> Dict[str, Any]:
        return {
            "project": {"name": project_title, "description": refined_prompt},
            "files": [],
            "tasks": [
                {
                    "task": "Implement based on user request",
                    "description": f"Implement: {refined_prompt}",
                    "module": "ProgrammingModule",
                    "output": "Working implementation",
                }
            ],
        }

    def validate_plan(self, plan: Dict[str, Any]) -> bool:
        try:
            return validate_plan(plan)
        except Exception as e:
            logger.warning(f"Plan validation failed: {e}")
            return False
