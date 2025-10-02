import json
import re
from typing import List, Dict, Any, Optional, Tuple

from memory.prompt_manager import PromptManager
from qllm.unified_llm import UnifiedLLM
from utils.ui_helpers import say_error, say_system


class AgenticService:
    """
    A general-purpose agentic template for LLM-driven workflows.
    Supports code generation, analysis, testing, and planning.
    """

    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager

        # Language configuration registry
        self.language_configs: Dict[str, Dict[str, Any]] = {
            "python": {"extensions": [".py"], "testing": "pytest"},
            "javascript": {"extensions": [".js", ".ts"], "testing": "jest"},
            "kotlin": {"extensions": [".kt"], "testing": "junit"},
            "java": {"extensions": [".java"], "testing": "junit"},
            "go": {"extensions": [".go"], "testing": "testing"},
            "rust": {"extensions": [".rs"], "testing": "cargo test"},
        }

        # Reusable system prompts (domain-specific expertise)
        self.system_prompts: Dict[str, str] = {
            "general": "You are an expert developer. Generate clean, idiomatic, production-ready code.",
            "testing": "You are a testing expert. Write comprehensive tests using best practices.",
            "analysis": "You are a senior reviewer. Analyze code quality, maintainability, and risks.",
            "planner": "You are a technical architect. Generate step-by-step actionable execution plans.",
        }

    # ---------------------------
    # Language Detection
    # ---------------------------
    def detect_language(self, text: str, file_context: Optional[str] = None) -> str:
        text_lower = text.lower()
        for lang, cfg in self.language_configs.items():
            if any(ext in text_lower for ext in cfg["extensions"]):
                return lang
        if "python" in text_lower or "django" in text_lower:
            return "python"
        if "kotlin" in text_lower or "android" in text_lower:
            return "kotlin"
        return "unknown"

    # ---------------------------
    # Prompt Builders
    # ---------------------------
    def build_system_prompt(self, task_type: str, language: Optional[str] = None) -> str:
        base = self.system_prompts.get(task_type, self.system_prompts["general"])
        if language and language in self.language_configs:
            base += f"\nTarget language: {language.capitalize()}. Use idiomatic best practices."
        return base

    def enhance_prompt(self, user_prompt: str, context: Optional[str] = None) -> str:
        enhanced = [user_prompt]
        if context:
            enhanced.append(f"\nPROJECT CONTEXT:\n{context}")
        enhanced.append("\nIMPORTANT: Generate complete, runnable, production-quality code.")
        return "\n".join(enhanced)

    # ---------------------------
    # Code Generation
    # ---------------------------
    def generate_code(
        self,
        prompt: str,
        language: Optional[str] = None,
        task_type: str = "general",
        file_context: Optional[str] = None,
    ) -> str:
        if not language:
            language = self.detect_language(prompt, file_context)
            if language == "unknown":
                language = "python"  # fallback

        system_message = self.build_system_prompt(task_type, language)
        user_message = self.enhance_prompt(prompt, file_context)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        try:
            response = self.llm.generate(messages, use_tools=True)
            code = response.strip()
            return self.self_correct(code, language)
        except Exception as e:
            say_error(f"Code generation failed: {e}")
            return ""

    # ---------------------------
    # Self-Correction
    # ---------------------------
    def self_correct(self, code: str, language: str) -> str:
        issues = self.analyze_code(code, language)
        if not issues:
            return code

        correction_prompt = f"""The following {language} code has issues:
{chr(10).join(f"- {i}" for i in issues)}

Correct and improve it while keeping functionality.
Code:
```{language}
{code}
```"""

        try:
            messages = [
                {"role": "system", "content": self.system_prompts["general"]},
                {"role": "user", "content": correction_prompt},
            ]
            corrected = self.llm.generate(messages, use_tools=False)
            return corrected.strip()
        except Exception as e:
            say_error(f"Correction failed: {e}")
            return code

    # ---------------------------
    # Analysis
    # ---------------------------
    def analyze_code(self, code: str, language: str) -> List[str]:
        issues = []
        if "!!" in code and language == "kotlin":
            issues.append("Unsafe non-null assertion (!!) found.")
        if "println" in code and language in ["kotlin", "java"]:
            issues.append("Use a logging framework instead of println.")
        if "eval(" in code and language == "python":
            issues.append("Use of eval() is dangerous.")
        return issues

    # ---------------------------
    # Testing
    # ---------------------------
    def generate_tests(self, code: str, language: str) -> str:
        test_prompt = f"""Write comprehensive unit tests in {language} for this code:

```{language}
{code}

Include:

Happy path tests

Edge cases

Error handling

Proper naming conventions """

try:
      messages = [
          {"role": "system", "content": self.system_prompts["testing"]},
          {"role": "user", "content": test_prompt},
      ]
      return self.llm.generate(messages, use_tools=False).strip()
  except Exception as e:
      say_error(f"Test generation failed: {e}")
      return ""

---------------------------

Planning

---------------------------

def generate_plan(self, goal: str) -> str: plan_prompt = f"""Generate a structured execution plan for this goal:


{goal}

Use numbered steps, focus on clarity and feasibility. """ try: messages = [ {"role": "system", "content": self.system_prompts["planner"]}, {"role": "user", "content": plan_prompt}, ] return self.llm.generate(messages, use_tools=False).strip() except Exception as e: say_error(f"Plan generation failed: {e}") return ""

---

This is a **flexible agentic scaffold**:  

- `detect_language()` → lightweight language inference  
- `build_system_prompt()` + `enhance_prompt()` → modular prompt construction  
- `generate_code()` → main entry for generation with self-correction loop  
- `analyze_code()` → detects common anti-patterns (expandable)  
- `generate_tests()` → attaches test generation pipeline  
- `generate_plan()` → task/architecture planner  

You can keep expanding `system_prompts` and `analyze_code()` just like you did for Kotlin.  

---

Want me to **extend this into a full multi-agent setup** (e.g., `CoderAgent`, `ReviewerAgent`, `TesterAgent`, `PlannerAgent` classes inheriting from `AgenticService`) so they can collaborate, or do you prefer a single flexible service class like above?

