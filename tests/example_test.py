# tests/test_example.py

from typing import Any, Generator

import pytest
from loguru import logger as base_loguru_logger

from src.core.config import Settings
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
    # Test with mock environment variables to avoid requiring actual config
    import os

    test_env = {
        "OPENAI_API_KEY": "test-key",
        "NOTION_API_KEY": "test-notion-key",
        "NOTION_DATABASE_ID": "test-db-id",
        "MASTER_RESUME_PATH": "/tmp/test.tex",
    }

    # Temporarily set env vars
    original_env: dict[str, str | None] = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        settings = Settings()  # type: ignore[call-arg]
        assert settings.LOG_LEVEL is not None
    finally:
        # Restore original environment
        for key in test_env:
            if original_env[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_env[key]  # type: ignore[assignment]


def test_logger_instance() -> None:
    """Test that the imported logger is a loguru.Logger instance."""
    assert isinstance(app_logger, type(base_loguru_logger))


def test_main_runs_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Test that src.main.main runs and logs expected messages."""
    import os

    test_env = {
        "OPENAI_API_KEY": "test-key",
        "NOTION_API_KEY": "test-notion-key",
        "NOTION_DATABASE_ID": "test-db-id",
        "MASTER_RESUME_PATH": "/tmp/test.tex",
    }

    # Temporarily set env vars
    original_env: dict[str, str | None] = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        with caplog.at_level("INFO"):
            # Mock the argument parsing and other services since main now requires arguments
            from unittest.mock import patch

            with (
                patch("src.main.parse_arguments") as mock_parse_args,
                patch("src.main.NotionService") as mock_notion,
                patch("src.main.ExtractorService") as mock_extractor,
                patch("src.main.convert_openai_response_to_notion_update") as mock_convert,
            ):
                # Setup mocks
                mock_args = type("Args", (), {"job_url": "https://test.com", "model": "gpt-4o"})()
                mock_parse_args.return_value = mock_args

                mock_notion_instance = mock_notion.return_value
                mock_notion_instance.get_database_schema.return_value = {"test": {"type": "title"}}

                mock_extractor_instance = mock_extractor.return_value
                mock_extractor_instance.extract_metadata_from_job_url.return_value = {"test": "value"}

                mock_convert.return_value = {"properties": {"test": {"rich_text": [{"text": {"content": "value"}}]}}}

                run_main_app()

        assert "Job Finder Assistant starting..." in caplog.text
        assert "Initializing services..." in caplog.text
        assert "Job Finder Assistant completed successfully!" in caplog.text

    finally:
        # Restore original environment
        for key in test_env:
            if original_env[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_env[key]  # type: ignore[assignment]
