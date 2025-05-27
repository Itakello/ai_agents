from src.core.config import settings
from src.core.logger import logger  # Import the configured loguru logger


def main() -> None:
    """Main function for the application."""
    logger.info("Application starting...")
    logger.debug(f"Current LOG_LEVEL: {settings.log_level}")

    # TODO: Add your application logic here
    logger.info("Application has finished its current task.")

    # Example of more detailed logging with loguru
    logger.success("This is a success message!")
    try:
        _result = 10 / 0  # Example: renamed to indicate it's for demonstration
    except ZeroDivisionError:
        logger.exception("An error occurred during calculation in main.")


if __name__ == "__main__":
    main()
