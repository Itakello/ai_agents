# tests/test_example.py

from typing import Any, Generator

import pytest
from loguru import logger as base_loguru_logger

from src.core.config import settings
from src.core.logger import logger as app_logger
from src.main import main as run_main_app


@pytest.fixture(autouse=True)
def _caplog_loguru_setup(caplog: pytest.LogCaptureFixture) -> Generator[None, Any, None]:
    """Fixture to propagate loguru messages to pytest's caplog."""
    # Ensure caplog captures loguru messages by adding its handler to loguru
    # Using a simple format for the captured messages to make assertions easier
    handler_id = base_loguru_logger.add(caplog.handler, format="{message}")
    yield
    # Clean up by removing the handler after the test
    base_loguru_logger.remove(handler_id)


def example_function_to_test(x: int) -> int:
    """An example function that adds 1 to the input."""
    return x + 1


def test_example_function() -> None:
    """An example test function."""
    assert example_function_to_test(3) == 4
    assert example_function_to_test(-1) == 0


@pytest.mark.skip(reason="Demonstrating a skipped test")
def test_another_example_skipped() -> None:
    assert True


def test_settings_load() -> None:
    assert settings.LOG_LEVEL is not None


def test_logger_instance() -> None:
    """Test that the imported logger is a loguru.Logger instance."""
    assert isinstance(app_logger, type(base_loguru_logger))


def test_main_runs_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Test that src.main.main runs and logs expected messages."""
    with caplog.at_level("INFO"):
        run_main_app()
    assert "Application starting..." in caplog.text
    assert "Application has finished its current task." in caplog.text
    assert "This is a success message!" in caplog.text
    # Check for the error log from the ZeroDivisionError example
    assert "An error occurred during calculation in main." in caplog.text
