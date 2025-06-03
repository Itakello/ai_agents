"""Tests for the configuration module."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

# Import the module under test
from src.core.config import Settings


class TestSettings:
    """Test the Settings class for configuration management."""

    def _set_required_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Helper to set required environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setenv("NOTION_API_KEY", "test_notion_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_db_id")
        monkeypatch.setenv("MASTER_RESUME_PATH", "/path/to/resume.tex")

    def _clear_all_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Helper to clear all relevant environment variables."""
        # Clear required environment variables
        for key in [
            "OPENAI_API_KEY",
            "NOTION_API_KEY",
            "NOTION_DATABASE_ID",
            "MASTER_RESUME_PATH",
        ]:
            monkeypatch.delenv(key, raising=False)

        # Clear optional environment variables
        for key in [
            "LOG_LEVEL",
            "PDFLATEX_COMMAND",
            "LATEXDIFF_COMMAND",
            "DEFAULT_MODEL_NAME",
            "DEFAULT_OUTPUT_DIR",
            "TEST_NOTION_PAGE_ID",
        ]:
            monkeypatch.delenv(key, raising=False)

    def _clear_optional_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Helper to clear only optional environment variables."""
        for key in [
            "PDFLATEX_COMMAND",
            "LATEXDIFF_COMMAND",
            "DEFAULT_MODEL_NAME",
            "DEFAULT_OUTPUT_DIR",
            "TEST_NOTION_PAGE_ID",
        ]:
            monkeypatch.delenv(key, raising=False)

    def test_required_settings_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that required settings raise validation errors when missing."""
        self._clear_all_env_vars(monkeypatch)

        with pytest.raises(ValidationError):
            # Create settings class that doesn't load from .env file
            class TestSettings(Settings):
                model_config = SettingsConfigDict(
                    env_file=None,
                    env_file_encoding="utf-8",
                    extra="ignore",
                    env_nested_delimiter="__",
                )

            # This will try to create settings with missing required fields
            TestSettings()  # type: ignore[call-arg]

    def test_required_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that settings are loaded correctly from environment variables."""
        # Set required environment variables
        self._set_required_env_vars(monkeypatch)

        # Create settings - should load from env vars
        settings = Settings()  # type: ignore[call-arg]

        # Verify settings were loaded correctly from environment
        assert settings.OPENAI_API_KEY == "test_openai_key"
        assert settings.NOTION_API_KEY == "test_notion_key"
        assert settings.NOTION_DATABASE_ID == "test_db_id"
        assert str(settings.MASTER_RESUME_PATH) == "/path/to/resume.tex"

    def test_required_settings_explicit_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that settings work when passed explicit arguments."""
        # Clear environment variables to ensure we're testing explicit args
        self._clear_all_env_vars(monkeypatch)

        # Create settings with explicit arguments
        settings = Settings(
            OPENAI_API_KEY="explicit_openai_key",
            NOTION_API_KEY="explicit_notion_key",
            NOTION_DATABASE_ID="explicit_db_id",
            MASTER_RESUME_PATH=Path("/explicit/path/to/resume.tex"),
        )

        # Verify explicit arguments take precedence
        assert settings.OPENAI_API_KEY == "explicit_openai_key"
        assert settings.NOTION_API_KEY == "explicit_notion_key"
        assert settings.NOTION_DATABASE_ID == "explicit_db_id"
        assert str(settings.MASTER_RESUME_PATH) == "/explicit/path/to/resume.tex"

    def test_optional_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that optional settings can be overridden via environment variables."""
        # Set required environment variables
        self._set_required_env_vars(monkeypatch)

        # Override optional settings via environment variables
        monkeypatch.setenv("DEFAULT_MODEL_NAME", "gpt-4-turbo")
        monkeypatch.setenv("DEFAULT_OUTPUT_DIR", "custom_output")

        # Create settings - should load from env vars
        settings = Settings()  # type: ignore[call-arg]

        assert settings.DEFAULT_MODEL_NAME == "gpt-4-turbo"  # From env var
        assert settings.DEFAULT_OUTPUT_DIR == Path("custom_output")  # From env var
        # Verify default values are set for other optional fields
        assert settings.PDFLATEX_COMMAND == "pdflatex"  # Default value

    def test_all_optional_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that all optional settings can be loaded from environment variables."""
        # Set required environment variables
        self._set_required_env_vars(monkeypatch)

        # Set optional environment variables
        monkeypatch.setenv("PDFLATEX_COMMAND", "/custom/path/pdflatex")
        monkeypatch.setenv("LATEXDIFF_COMMAND", "/custom/path/latexdiff")
        monkeypatch.setenv("TEST_NOTION_PAGE_ID", "test_page_123")

        # Create settings without explicit arguments - should load from env vars
        settings = Settings()  # type: ignore[call-arg]

        assert settings.PDFLATEX_COMMAND == "/custom/path/pdflatex"
        assert settings.LATEXDIFF_COMMAND == "/custom/path/latexdiff"
        assert settings.TEST_NOTION_PAGE_ID == "test_page_123"
        assert settings.DEFAULT_MODEL_NAME == "gpt-4.1"  # Default value
        assert settings.DEFAULT_OUTPUT_DIR == Path("output")  # Default value

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that default values are used when no environment variables are set."""
        # Set only required environment variables
        self._set_required_env_vars(monkeypatch)

        # Clear optional environment variables to test defaults
        self._clear_optional_env_vars(monkeypatch)

        settings = Settings()  # type: ignore[call-arg]

        # Verify default values are used
        assert settings.PDFLATEX_COMMAND == "pdflatex"
        assert settings.LATEXDIFF_COMMAND == "latexdiff"
        assert settings.DEFAULT_MODEL_NAME == "gpt-4.1"
        assert settings.DEFAULT_OUTPUT_DIR == Path("output")
        assert settings.TEST_NOTION_PAGE_ID is None

    def test_api_key_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that API key validation works correctly."""
        # Clear all env vars first
        self._clear_all_env_vars(monkeypatch)

        # Test with too short API key
        with pytest.raises(ValidationError):
            Settings(
                OPENAI_API_KEY="short",  # Too short
                NOTION_API_KEY="test_notion_key",
                NOTION_DATABASE_ID="test_db_id",
                MASTER_RESUME_PATH=Path("/path/to/resume.tex"),
            )

        # Test with empty API key
        with pytest.raises(ValidationError):
            Settings(
                OPENAI_API_KEY="",  # Empty
                NOTION_API_KEY="test_notion_key_long_enough",
                NOTION_DATABASE_ID="test_db_id",
                MASTER_RESUME_PATH=Path("/path/to/resume.tex"),
            )

        # Test with valid API keys
        settings = Settings(
            OPENAI_API_KEY="valid_openai_key_long_enough",
            NOTION_API_KEY="valid_notion_key_long_enough",
            NOTION_DATABASE_ID="test_db_id",
            MASTER_RESUME_PATH=Path("/path/to/resume.tex"),
        )
        assert settings.OPENAI_API_KEY == "valid_openai_key_long_enough"

    def test_resume_path_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that resume path validation works correctly."""
        # Clear all env vars first
        self._clear_all_env_vars(monkeypatch)

        # Test with non-.tex file
        with pytest.raises(ValidationError):
            Settings(
                OPENAI_API_KEY="valid_openai_key_long_enough",
                NOTION_API_KEY="valid_notion_key_long_enough",
                NOTION_DATABASE_ID="test_db_id",
                MASTER_RESUME_PATH=Path("/path/to/resume.pdf"),  # Wrong extension
            )

        # Test with valid .tex file
        settings = Settings(
            OPENAI_API_KEY="valid_openai_key_long_enough",
            NOTION_API_KEY="valid_notion_key_long_enough",
            NOTION_DATABASE_ID="test_db_id",
            MASTER_RESUME_PATH=Path("/path/to/resume.tex"),  # Correct extension
        )
        assert str(settings.MASTER_RESUME_PATH) == "/path/to/resume.tex"

    def test_log_level_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that log level validation works correctly."""
        # Set required env vars
        self._set_required_env_vars(monkeypatch)

        # Test with invalid log level
        with pytest.raises(ValidationError):
            Settings(LOG_LEVEL="INVALID")  # type: ignore[call-arg]

        # Test with valid log level (should be converted to uppercase)
        monkeypatch.setenv("LOG_LEVEL", "debug")
        settings = Settings()  # type: ignore[call-arg]
        assert settings.LOG_LEVEL == "DEBUG"

    def test_get_settings_singleton(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get_settings returns the same instance."""
        from src.core.config import get_settings

        # Set required env vars
        self._set_required_env_vars(monkeypatch)

        # Get settings twice
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance
        assert settings1 is settings2
