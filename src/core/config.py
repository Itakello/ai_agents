"""Configuration settings for the Job Finder Assistant.

This module provides a Settings class that loads configuration from environment variables
with support for .env files. It uses pydantic for validation and type conversion.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required settings:
        OPENAI_API_KEY: API key for OpenAI
        NOTION_API_KEY: API key for Notion
        NOTION_DATABASE_ID: ID of the Notion database to use
        MASTER_RESUME_PATH: Path to the master resume .tex file

    Optional settings with defaults:
        LOG_LEVEL: Logging level (default: "INFO")
        PDFLATEX_COMMAND: Path to pdflatex executable (default: "pdflatex")
        LATEXDIFF_COMMAND: Path to latexdiff executable (default: "latexdiff")
        DEFAULT_MODEL_NAME: OpenAI model to use (default: "gpt-4.1")
        DEFAULT_OUTPUT_DIR: Directory for output files (default: "./output")
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    # Required settings
    OPENAI_API_KEY: str
    NOTION_API_KEY: str
    NOTION_DATABASE_ID: str
    MASTER_RESUME_PATH: Path

    # Optional settings with defaults
    LOG_LEVEL: str = "INFO"
    PDFLATEX_COMMAND: str = "pdflatex"
    LATEXDIFF_COMMAND: str = "latexdiff"
    DEFAULT_MODEL_NAME: str = "gpt-4.1"
    DEFAULT_OUTPUT_DIR: Path = Path("output")
    TEST_NOTION_PAGE_ID: str | None = None


if __name__ == "__main__":
    settings = Settings()  # type: ignore[call-arg]
    print("Configuration loaded successfully:")
    print(f"LOG_LEVEL: {settings.LOG_LEVEL}")
    print(f"DEFAULT_MODEL_NAME: {settings.DEFAULT_MODEL_NAME}")
    print(f"DEFAULT_OUTPUT_DIR: {settings.DEFAULT_OUTPUT_DIR}")
    print(f"PDFLATEX_COMMAND: {settings.PDFLATEX_COMMAND}")
    print(f"LATEXDIFF_COMMAND: {settings.LATEXDIFF_COMMAND}")

    # Show which required settings are missing (will raise ValidationError if missing)
    try:
        print(f"OPENAI_API_KEY: {'*' * 10}...{settings.OPENAI_API_KEY[-4:]}")
        print(f"NOTION_API_KEY: {'*' * 10}...{settings.NOTION_API_KEY[-4:]}")
        print(f"NOTION_DATABASE_ID: {settings.NOTION_DATABASE_ID}")
        print(f"MASTER_RESUME_PATH: {settings.MASTER_RESUME_PATH}")
    except Exception as e:
        print(f"Missing required settings: {e}")
