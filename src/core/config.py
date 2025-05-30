"""Configuration settings for the Job Finder Assistant.

This module provides a Settings class that loads configuration from environment variables
with support for .env files. It uses pydantic for validation and type conversion.
"""

from pathlib import Path

from pydantic import Field, field_validator
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
    OPENAI_API_KEY: str = Field(..., description="API key for OpenAI")
    NOTION_API_KEY: str = Field(..., description="API key for Notion")
    NOTION_DATABASE_ID: str = Field(..., description="ID of the Notion database to use")
    MASTER_RESUME_PATH: Path = Field(..., description="Path to the master resume .tex file")

    # Optional settings with defaults
    LOG_LEVEL: str = "INFO"
    PDFLATEX_COMMAND: str = "pdflatex"
    LATEXDIFF_COMMAND: str = "latexdiff"
    DEFAULT_MODEL_NAME: str = "gpt-4.1"
    DEFAULT_OUTPUT_DIR: Path = Path("output")
    TEST_NOTION_PAGE_ID: str | None = None

    # OpenAI API settings
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_TIMEOUT_SECONDS: int = 30

    # Default CLI settings
    DEFAULT_EXTRACTION_METHOD: str = "crawl4ai_plus_gpt"
    DEFAULT_EXPORT_PDF_DIR: str = "exported_pdfs"

    # Crawl4AI settings
    CRAWL4AI_HEADLESS: bool = True
    CRAWL4AI_TIMEOUT_SECONDS: int = 30
    CRAWL4AI_USER_AGENT: str = "Job-Finder-Assistant/1.0"
    CRAWL4AI_MAX_RETRIES: int = 3
    CRAWL4AI_RETRY_DELAY_SECONDS: int = 2
    MAX_CONTENT_LENGTH_CHARS: int = 500000

    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_TTL_HOURS: int = 24
    CACHE_MAX_ENTRIES: int = 1000
    CACHE_DIRECTORY: Path = Path(".cache")

    # PDF Export settings
    PDF_MAIN_FONT: str = "FiraCode Nerd Font"
    PDF_SANS_FONT: str = "FiraCode Nerd Font"
    PDF_MONO_FONT: str = "FiraCode Nerd Font Mono"
    PDF_MARGIN: str = "1in"
    PDF_FONT_SIZE: str = "11pt"
    PDF_LINE_STRETCH: str = "1.2"
    PDF_ENGINE_PRIMARY: str = "xelatex"
    PDF_ENGINE_FALLBACK: str = "lualatex"

    # File paths and directories
    PROMPTS_DIRECTORY: Path = Path("prompts")
    METADATA_EXTRACTION_PROMPT_FILE: str = "sys_prompt_extract_metadata.txt"
    CRAWL4AI_PROMPT_FILE: str = "crawl4ai_plus_gpt_prompt.txt"
    TEMP_DIRECTORY: Path = Path("tmp")

    # Performance and reliability settings
    API_KEY_MIN_LENGTH: int = 10
    MAX_API_RETRIES_ON_FAILURE: int = 3
    API_RETRY_DELAY_SECONDS: float = 1.0
    REQUEST_BACKOFF_MULTIPLIER: float = 2.0
    MAX_OUTPUT_FILES_TO_KEEP: int = 100

    @field_validator("OPENAI_API_KEY", "NOTION_API_KEY")
    @classmethod
    def validate_api_keys(cls, v: str) -> str:
        """Validate API keys are non-empty and have reasonable length."""
        # Use the default value since we can't access other field values in field validators
        min_length = 10  # We'll use the API_KEY_MIN_LENGTH default
        if not v or len(v.strip()) < min_length:
            raise ValueError(f"API key must be at least {min_length} characters long")
        return v.strip()

    @field_validator("MASTER_RESUME_PATH")
    @classmethod
    def validate_resume_path(cls, v: Path | str) -> Path:
        """Validate resume path exists and is a .tex file."""
        if isinstance(v, str):
            v = Path(v)
        if not v.suffix == ".tex":
            raise ValueError("Resume path must be a .tex file")
        # Note: We don't check if file exists here as it might not exist yet
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator("OPENAI_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is between 0 and 2."""
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("DEFAULT_EXTRACTION_METHOD")
    @classmethod
    def validate_extraction_method(cls, v: str) -> str:
        """Validate extraction method is supported."""
        valid_methods = {"openai_web_search", "crawl4ai_plus_gpt"}
        if v not in valid_methods:
            raise ValueError(f"Extraction method must be one of: {', '.join(valid_methods)}")
        return v


# Global settings instance - using a function to ensure it's only created once
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance.

    This ensures we only load settings once and cache them.
    """
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


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
