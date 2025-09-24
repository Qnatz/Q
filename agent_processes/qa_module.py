import os
from datetime import datetime
from typing import List, Dict, Any

class QAModule:
    """
    Lightweight QA agent:
      - Verifies expected files exist and are non-empty
      - Optionally validates against the plan's declared files
      - Produces a Markdown report at project_state/test_report.md
    """

    def __init__(self, llm=None, tool_registry=None):
        self.llm = llm  # optional (not required for basic checks)
        self.tool_registry = tool_registry # Store tool_registry

    def _ensure_dir(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def _read_safe(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def test(self, implemented_files: List[str], plan: Dict[str, Any] | None = None) -> str:
        """
        Runs simple QA checks using StepwiseQATool and writes project_state/test_report.md.
        """
        if self.tool_registry:
            qa_tool_instance = self.tool_registry.get_tool("stepwise_qa")
            if qa_tool_instance:
                return qa_tool_instance.run(implemented_files=implemented_files, plan=plan)
            else:
                raise ValueError("StepwiseQATool not found in tool registry.")
        else:
            raise ValueError("Tool registry not provided to QAModule.")
