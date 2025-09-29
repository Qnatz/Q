# management_module.py
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import logging

from core.llm_service import LLMService
from utils.json_utils import safe_json_extract
from memory.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

@dataclass
class ReviewResult:
    approved: bool
    feedback: str
    concerns: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None

@dataclass
class CorrectionResult:
    spec: Dict[str, Any]
    notes: str
    priority: str = "medium"  # low, medium, high, critical

class ManagementModule:
    def __init__(self, llm_service: LLMService, prompt_manager: PromptManager):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self._max_retries = 2
        self.logger = logging.getLogger(__name__)

    def _load_prompt(self, prompt_name: str) -> str:
        """Load prompt with proper error handling"""
        prompt_content = self.prompt_manager.get_prompt(prompt_name)
        if not prompt_content:
            logger.error(f"Prompt '{prompt_name}' not found")
            raise ValueError(f"Required prompt '{prompt_name}' not available")
        return prompt_content

    def review_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Review project plan with comprehensive validation"""
        self.logger.info("Reviewing project plan")
        
        try:
            system_prompt_content = self._load_prompt("orchestrator/manager_review_plan")
            
            prompt = f"Plan to review:\n{json.dumps(plan, indent=2)}"
            
            for attempt in range(self._max_retries):
                try:
                    raw_response = self.llm_service.llm.generate([
                        {"role": "system", "content": system_prompt_content},
                        {"role": "user", "content": prompt}
                    ], use_tools=False)
                    
                    parsed = safe_json_extract(raw_response)
                    if self._validate_review_response(parsed):
                        logger.info(f"Plan review completed: {'Approved' if parsed['approved'] else 'Rejected'}")
                        return parsed
                    
                    logger.warning(f"Invalid review response format on attempt {attempt + 1}")
                    
                except Exception as e:
                    logger.error(f"Review attempt {attempt + 1} failed: {e}")
            
            # Fallback to auto-approval with warning
            logger.warning("All review attempts failed, using auto-approval fallback")
            return {
                "approved": True, 
                "feedback": "Auto-approved after review failure",
                "concerns": ["Review system unavailable"],
                "suggestions": ["Proceed with caution"]
            }
            
        except Exception as e:
            logger.error(f"Plan review failed: {e}")
            return {
                "approved": False,
                "feedback": f"Review system error: {str(e)}",
                "concerns": ["System malfunction"],
                "suggestions": ["Please try again or contact support"]
            }

    def _validate_review_response(self, response: Any) -> bool:
        """Validate the structure of review response"""
        if not isinstance(response, dict):
            return False
        
        if "approved" not in response:
            return False
            
        if not isinstance(response["approved"], bool):
            return False
            
        if "feedback" not in response or not isinstance(response["feedback"], str):
            return False
            
        return True

    def provide_correction(self, implementation: Dict, validation_error: str) -> Dict:
        """Provide corrective specifications for implementation issues"""
        logger.info("Generating correction specifications")
        
        try:
            system_prompt_content = self._load_prompt("orchestrator/manager_provide_correction")
            
            prompt = f"""
Implementation with issue:
{json.dumps(implementation, indent=2)}

Validation error encountered:
{validation_error}

Please provide specific corrections:
"""
            raw_response = self.llm_service.llm.generate([
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": prompt}
            ], use_tools=False)
            
            parsed = safe_json_extract(raw_response)
            if self._validate_correction_response(parsed):
                return parsed
            
            # Fallback correction
            logger.warning("Using fallback correction specification")
            return {
                "spec": {"notes": f"Fix validation error: {validation_error}"},
                "notes": "Automated fallback correction",
                "priority": "high"
            }
            
        except Exception as e:
            logger.error(f"Correction generation failed: {e}")
            return {
                "spec": {"emergency_fix": True, "notes": "System error - manual review required"},
                "notes": f"Error in correction system: {e}",
                "priority": "critical"
            }

    def _validate_correction_response(self, response: Any) -> bool:
        """Validate correction response structure"""
        if not isinstance(response, dict):
            return False
            
        if "spec" not in response or not isinstance(response["spec"], dict):
            return False
            
        if "notes" not in response or not isinstance(response["notes"], str):
            return False
            
        return True