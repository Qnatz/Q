"""LLM utilities for CrewAI integration"""

from typing import Dict, Any
from qllm.config import Config
from qllm.unified_llm import UnifiedLLM
from qllm.custom_crewai_llm import CustomCrewAI_LLM


def get_crewai_llm(
    agent_name: str, llm_mode: str, llama_endpoint: str
) -> CustomCrewAI_LLM:
    """Get LLM configuration for CrewAI agents"""
    config = Config(
        backend="http" if llm_mode == "offline" else "gemini",
        api_base=llama_endpoint,
        model="llama",
    )

    unified_llm = UnifiedLLM(cfg=config)

    return CustomCrewAI_LLM(unified_llm=unified_llm)
