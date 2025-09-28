from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    model: str = "gemini-pro"
    llm_mode: str = "offline"
    llama_endpoint: str = "http://127.0.0.1:8080"
    log_level: str = "DEBUG"
    api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    sandbox: bool = False
    sandbox_image: Optional[str] = None
    debug: bool = False
    prompt: Optional[str] = None
    prompt_interactive: Optional[str] = None
    all_files: bool = False
    show_memory_usage: bool = False
    yolo: bool = False
    telemetry: bool = False
    telemetry_target: Optional[str] = None
    telemetry_otlp_endpoint: Optional[str] = None
    telemetry_log_prompts: bool = False
    telemetry_outfile: Optional[str] = None
    allowed_mcp_server_names: Optional[List[str]] = None
    experimental_acp: bool = False
    extensions: Optional[List[str]] = None
    list_extensions: bool = False
    ide_mode: bool = False
    proxy: Optional[str] = None
    checkpointing: bool = False

    class Config:
        env_prefix = "QAI_"
        env_file = ".env"


settings = Settings()
