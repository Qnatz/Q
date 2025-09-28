"""Configuration dataclass for UnifiedLLM."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    # backend: "gemini" | "openai" | "http" | "cli"
    backend: str = "gemini"

    # Common controls
    temperature: float = 0.7
    max_tokens: int = 4096
    max_tool_loops: int = 4

    # OpenAI-compatible HTTP backend (e.g., local llama.cpp server)
    api_base: str = "http://127.0.0.1:8080"
    model: str = "llama"
    api_key: Optional[str] = None  # if required by HTTP backend

    # Gemini specific
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key_env: str = "GEMINI_API_KEY"

    # CLI backend
    cli_path: str = "llama"
    cli_model_path: Optional[str] = None
