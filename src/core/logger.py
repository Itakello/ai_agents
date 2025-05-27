import sys

from loguru import logger

from src.core.config import settings  # Assuming your config is in src.core.config

# Remove default handler and add a new one with the desired format and level
logger.remove()
logger.add(
    sys.stderr,  # Sink: where the log messages are sent (e.g., sys.stderr, file path)
    level=settings.log_level.upper(),  # Minimum log level
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,  # Enable colorized output if the sink supports it
    backtrace=True,  # Enable enhanced traceback for exceptions
    diagnose=True,  # Add extended diagnostic information on errors
)

# Optional: Add a file sink if you want to log to a file as well
# from pathlib import Path
# LOGS_DIR = Path(__file__).resolve().parent.parent.parent / 'logs'
# LOGS_DIR.mkdir(exist_ok=True)
# logger.add(
#     LOGS_DIR / "app.log",
#     rotation="10 MB",
#     retention="10 days",
#     level="DEBUG"
# )

# Loguru 'logger' is configured and can be imported/used directly.

# Example usage (can be removed or kept for quick testing):
if __name__ == "__main__":
    logger.debug("This is a debug message from loguru.")
    logger.info("This is an info message from loguru.")
    logger.warning("This is a warning message from loguru.")
    logger.error("This is an error message from loguru.")
    logger.critical("This is a critical message (loguru).")

    try:
        x = 1 / 0
    except ZeroDivisionError:
        logger.exception("Caught an exception!")
