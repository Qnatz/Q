import os
from typing import List
import logging
from core.llm_service import LLMService
from memory.prompt_manager import PromptManager # Import PromptManager
from tools.base_tool_classes import ToolExecutionStatus

logger = logging.getLogger(__name__)

class ReviewModule:
    """
    Code review agent:
      - Uses LLM (if available) to produce human-readable feedback
      - Falls back to simple heuristics when LLM is not provided
      - Writes project_state/code_review_report.md
    """

    def __init__(self, llm_service: LLMService = None, prompt_manager: PromptManager = None, tool_registry=None):
        self.llm_service = llm_service
        self.prompt_manager = prompt_manager
        self.tool_registry = tool_registry
        self.system_prompt_name = "orchestrator/review"

    def _ensure_dir(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def _llm_review(self, filepath: str, content: str) -> str:
        system_prompt_content = self.prompt_manager.get_prompt(self.system_prompt_name)
        if not system_prompt_content:
            logger.error(f"System prompt '{self.system_prompt_name}' not found in memory.")
            raise ValueError(f"System prompt '{self.system_prompt_name}' not found in memory.")

        prompt = f"""
File: {filepath}

Provide a concise review with:
- Summary (what the file does)
- Correctness & potential bugs
- Readability & maintainability
- Security & performance concerns
- Actionable recommendations (bullet points)
Limit to ~200-300 words.
Code begins below:

{content}

"""
        try:
            # If your UnifiedLLM exposes .generate(messages) use that API; otherwise adapt as needed.
            return self.llm_service.llm.generate([{"role": "system", "content": system_prompt_content}, {"role": "user", "content": prompt}]) if self.llm_service else ""
        except Exception:
            return ""

    def _heuristic_review(self, filepath: str, content: str) -> str:
        # Minimal fallback when no LLM is available
        lines = []
        lines.append(f"**Heuristic Review for {filepath}**")
        if not content.strip():
            lines.append("- File is empty or unreadable.")
            return "\n".join(lines)

        # Very basic flags
        if "TODO" in content or "todo" in content.lower():
            lines.append("- Contains TODOs; consider resolving before release.")
        if len(content) > 8000:
            lines.append("- File is large; consider splitting into modules for maintainability.")
        if filepath.endswith((".js", ".ts")) and "console.log" in content:
            lines.append("- Remove debugging `console.log` statements in production.")

        if not lines:
            lines.append("- No obvious issues detected by heuristics.")
        return "\n".join(lines)

    def review(self, implemented_files: List[str]) -> str:
        """
        Generates a code review report for the implemented files using StepwiseReviewTool.

        Returns:
          Path to the generated review report.
        """
        if self.tool_registry:
            result = self.tool_registry.execute_tool(
                "stepwise_review",
                {"implemented_files": implemented_files}
            )
            if result.status == ToolExecutionStatus.SUCCESS:
                return result.result
            else:
                logger.error(f"StepwiseReviewTool execution failed: {result.error_message}")
                raise ValueError(f"StepwiseReviewTool execution failed: {result.error_message}")
        else:
            logger.error("Tool registry not provided to ReviewModule.")
            raise ValueError("Tool registry not provided to ReviewModule.")
