"""Tests for the configuration module."""

from pathlib import Path

import pytest
from pydantic import ValidationError

# Import the module under test
from src.core.config import Settings


class TestSettings:
    """Test the Settings class for configuration management."""

    def test_required_settings_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that required settings raise validation errors when missing."""
        # Clear all required environment variables
        for key in [
            "OPENAI_API_KEY",
            "NOTION_API_KEY",
            "NOTION_DATABASE_ID",
            "MASTER_RESUME_PATH",
        ]:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ValidationError):
            # This will try to create settings with missing required fields
            Settings()  # type: ignore[call-arg]  # We're testing the error case

    def test_required_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that settings are loaded correctly from environment variables."""
        # Set required environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setenv("NOTION_API_KEY", "test_notion_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_db_id")
        monkeypatch.setenv("MASTER_RESUME_PATH", "/path/to/resume.tex")

        settings = Settings(
            OPENAI_API_KEY="test_openai_key",
            NOTION_API_KEY="test_notion_key",
            NOTION_DATABASE_ID="test_db_id",
            MASTER_RESUME_PATH=Path("/path/to/resume.tex"),
        )
        # Create settings without explicit arguments - should load from env vars
        settings = Settings()  # type: ignore[call-arg]

        # Verify settings were loaded correctly from environment
        assert settings.OPENAI_API_KEY == "test_openai_key"
        assert settings.NOTION_API_KEY == "test_notion_key"
        assert settings.NOTION_DATABASE_ID == "test_db_id"
        assert str(settings.MASTER_RESUME_PATH) == "/path/to/resume.tex"

    def test_required_settings_explicit_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that settings work when passed explicit arguments."""
        # Clear environment variables to ensure we're testing explicit args
        for key in ["OPENAI_API_KEY", "NOTION_API_KEY", "NOTION_DATABASE_ID", "MASTER_RESUME_PATH"]:
            monkeypatch.delenv(key, raising=False)

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
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setenv("NOTION_API_KEY", "test_notion_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_db_id")
        monkeypatch.setenv("MASTER_RESUME_PATH", "/path/to/resume.tex")
        # Override optional settings via environment variables
        monkeypatch.setenv("DEFAULT_MODEL_NAME", "gpt-4-turbo")
        monkeypatch.setenv("DEFAULT_OUTPUT_DIR", "custom_output")
        settings = Settings(
            OPENAI_API_KEY="test_openai_key",
            NOTION_API_KEY="test_notion_key",
            NOTION_DATABASE_ID="test_db_id",
            MASTER_RESUME_PATH=Path("/path/to/resume.tex"),
            DEFAULT_MODEL_NAME="gpt-4.1",
            DEFAULT_OUTPUT_DIR=Path("custom_output"),
        )

        # Create settings without explicit arguments - should load from env vars
        settings = Settings()  # type: ignore[call-arg]

        assert settings.DEFAULT_MODEL_NAME == "gpt-4-turbo"  # From env var
        assert settings.DEFAULT_OUTPUT_DIR == Path("custom_output")  # From env var
        # Verify default values are set for other optional fields
        assert settings.PDFLATEX_COMMAND == "pdflatex"  # Default value

    def test_all_optional_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that all optional settings can be loaded from environment variables."""
        # Set required environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setenv("NOTION_API_KEY", "test_notion_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_db_id")
        monkeypatch.setenv("MASTER_RESUME_PATH", "/path/to/resume.tex")
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
        monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
        monkeypatch.setenv("NOTION_API_KEY", "test_notion_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_db_id")
        monkeypatch.setenv("MASTER_RESUME_PATH", "/path/to/resume.tex")

        # Clear optional environment variables to test defaults
        for key in [
            "PDFLATEX_COMMAND",
            "LATEXDIFF_COMMAND",
            "DEFAULT_MODEL_NAME",
            "DEFAULT_OUTPUT_DIR",
            "TEST_NOTION_PAGE_ID",
        ]:
            monkeypatch.delenv(key, raising=False)

        settings = Settings()  # type: ignore[call-arg]

        # Verify default values are used
        assert settings.PDFLATEX_COMMAND == "pdflatex"
        assert settings.LATEXDIFF_COMMAND == "latexdiff"
        assert settings.DEFAULT_MODEL_NAME == "gpt-4.1"
        assert settings.DEFAULT_OUTPUT_DIR == Path("output")
        assert settings.TEST_NOTION_PAGE_ID is None
