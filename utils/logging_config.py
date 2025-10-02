import logging
import os
from core.settings import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("agent_manager.log"),
        ],
    )
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("memory.prompt_manager").setLevel(logging.ERROR)
    logging.getLogger("qllm.backends").setLevel(logging.DEBUG)
