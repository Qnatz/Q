import logging
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Create a more robust logger instance
logger = logging.getLogger("QaiRAG")
logger.setLevel(LOG_LEVEL)

# Add file handler for persistent logs
file_handler = logging.FileHandler("qai_rag.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)
