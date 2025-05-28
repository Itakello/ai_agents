import os
import sys
from pathlib import Path

from loguru import logger


def _load_env_file() -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip("\"'")
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value


def _configure_logger() -> None:
    """Configure loguru logger with settings from environment or defaults."""
    # Load .env file first
    _load_env_file()

    # Use environment variable or default for log level
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Remove default handler and add a new one with the desired format and level
    logger.remove()
    logger.add(
        sys.stderr,  # Sink: where the log messages are sent (e.g., sys.stderr, file path)
        level=log_level,  # Minimum log level
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


# Configure logger on import
_configure_logger()

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
