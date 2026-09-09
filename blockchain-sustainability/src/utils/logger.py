"""
Logging utility using Loguru.
Import `logger` from this module everywhere in the project.
"""
import sys
from loguru import logger
from src.utils.config import LOG_LEVEL

logger.remove()   # drop default handler
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
           "<level>{message}</level>",
    colorize=True,
)
logger.add(
    "logs/app.log",
    level="DEBUG",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
)

__all__ = ["logger"]
