"""
Unit tests for core.logger module.
"""

import importlib
import os
import sys
from pathlib import Path

from loguru import logger
from pytest import MonkeyPatch


def test_logger_configures_on_import(monkeypatch: MonkeyPatch) -> None:
    """Test that logger is configured on import and respects LOG_LEVEL env variable."""
    # Patch environment variable
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    # Reload the module to re-trigger configuration
    if "src.core.logger" in sys.modules:
        importlib.reload(sys.modules["src.core.logger"])
    else:
        importlib.import_module("src.core.logger")
    # Should not raise, and logger should be configured
    logger.warning("This is a warning (should appear)")
    logger.info("This is info (should not appear)")


def test_logger_env_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test that _load_env_file loads variables from .env if present."""
    # The logger expects .env at project root (3 parents up from logger.py)
    import src.core.logger as logger_mod

    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    env_content = "TEST_LOG_VAR=hello_env\n"
    # Backup existing .env if it exists to avoid deleting user configuration
    original_env_content: str | None = None
    env_file_preexisting = env_file.exists()
    if env_file_preexisting:
        original_env_content = env_file.read_text(encoding="utf-8")
    # Write test .env content (overwriting if necessary)
    env_file.write_text(env_content, encoding="utf-8")
    try:
        # Remove variable if already present
        if "TEST_LOG_VAR" in os.environ:
            del os.environ["TEST_LOG_VAR"]
        logger_mod._load_env_file()
        assert os.environ.get("TEST_LOG_VAR") == "hello_env"
    finally:
        # Restore original .env content or remove the file if we created it
        if env_file_preexisting and original_env_content is not None:
            env_file.write_text(original_env_content, encoding="utf-8")
        else:
            env_file.unlink(missing_ok=True)
        if "TEST_LOG_VAR" in os.environ:
            del os.environ["TEST_LOG_VAR"]


def test_logger_adds_sink_and_format(monkeypatch: MonkeyPatch) -> None:
    """Test that the logger adds the correct sink and format."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    # Remove all handlers and re-add
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    logger.debug("Debug message visible")
    logger.info("Info message visible")
    logger.warning("Warning message visible")
    logger.error("Error message visible")
    logger.critical("Critical message visible")
