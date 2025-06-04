"""Tests for the ExtractorService class."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.metadata_extraction.extractor_service import ExtractorService


class TestExtractorService:
    """Test suite for the ExtractorService class."""

    @pytest.fixture
    def mock_openai_client(self) -> Generator[MagicMock]:
        """Create a mock OpenAI client."""
        mock_client = MagicMock()
        mock_client.get_response.return_value = '{"job_title": "Software Engineer", "company": "Tech Corp"}'
        yield mock_client

    @pytest.fixture
    def mock_notion_service(self) -> Generator[MagicMock]:
        """Create a mock Notion service."""
        mock_service = MagicMock()
        yield mock_service

    @pytest.fixture
    def sample_notion_schema(self) -> dict[str, Any]:
        """Create a sample Notion database schema for testing."""
        return {
            "Job Title": {"id": "title", "type": "title"},
            "Company": {"id": "comp", "type": "rich_text"},
            "Status": {
                "id": "stat",
                "type": "status",
                "status": {
                    "options": [
                        {"name": "Applied", "id": "1", "color": "blue"},
                        {"name": "Interview", "id": "2", "color": "yellow"},
                        {"name": "Rejected", "id": "3", "color": "red"},
                    ]
                },
            },
            "Salary": {"id": "sal", "type": "number"},
            "Remote": {"id": "rem", "type": "checkbox"},
            "Skills": {
                "id": "skills",
                "type": "multi_select",
                "multi_select": {
                    "options": [
                        {"name": "Python", "id": "py", "color": "blue"},
                        {"name": "JavaScript", "id": "js", "color": "yellow"},
                        {"name": "React", "id": "react", "color": "green"},
                    ]
                },
            },
            "Application Date": {"id": "date", "type": "date"},
            "Contact Email": {"id": "email", "type": "email"},
            "Company Website": {"id": "url", "type": "url"},
            # Read-only fields that should be ignored
            "Created Time": {"id": "created", "type": "created_time"},
            "Last Edited": {"id": "edited", "type": "last_edited_time"},
        }

    @pytest.fixture
    def sample_job_description(self) -> str:
        """Create a sample job description for testing."""
        return """
        Software Engineer Position at Tech Corp

        We are looking for a talented Software Engineer to join our team.

        Responsibilities:
        - Develop web applications using Python and JavaScript
        - Work with React frontend framework
        - Collaborate with cross-functional teams

        Requirements:
        - Bachelor's degree in Computer Science
        - 3+ years of experience with Python
        - Experience with React and modern web technologies
        - Strong problem-solving skills

        Benefits:
        - Competitive salary: $80,000 - $120,000
        - Remote work options available
        - Health insurance and 401k

        Apply by sending your resume to jobs@techcorp.com
        Visit our website: https://techcorp.com
        """

    def test_init(self, mock_openai_client: MagicMock, mock_notion_service: MagicMock) -> None:
        """Test that the ExtractorService is initialized correctly."""
        # Act
        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Assert
        assert service.openai_client == mock_openai_client
        assert service.notion_service == mock_notion_service

# New fixtures and tests

    @pytest.fixture
    def mock_url_cache(self) -> Generator[MagicMock, None, None]:
        """Create a mock URLCache instance."""
        mock_cache = MagicMock()
        yield mock_cache

    def test_extract_with_openai_web_search(
        self,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Ensure OpenAI web search extraction calls the client correctly."""
        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Mock settings and helper functions
        settings = MagicMock()
        settings.PROMPTS_DIRECTORY = Path("tmp")
        settings.METADATA_EXTRACTION_PROMPT_FILE = "prompt.txt"
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.get_settings", lambda: settings
        )
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.read_file_content", lambda _path: "URL: {{URL}}"
        )
        openai_schema = {"type": "object"}
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.create_openai_schema_from_notion_database",
            lambda _schema, _add: openai_schema,
        )

        mock_openai_client.get_structured_response.return_value = {"job_title": "Engineer"}

        result = service._extract_with_openai_web_search(
            "https://example.com/job",
            sample_notion_schema,
            "gpt-4o",
        )

        assert result == {"job_title": "Engineer"}
        mock_openai_client.get_structured_response.assert_called_once_with(
            sys_prompt="URL: https://example.com/job",
            user_prompt=None,
            model_name="gpt-4o",
            schema=openai_schema,
            use_web_search=True,
        )

    def test_extract_with_crawl4ai_plus_gpt_uses_cache(
        self,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        mock_url_cache: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify cached markdown is used when available."""
        service = ExtractorService(mock_openai_client, mock_notion_service)
        service.url_cache = mock_url_cache
        mock_url_cache.get_cached_content.return_value = "cached markdown"

        settings = MagicMock()
        settings.PROMPTS_DIRECTORY = Path("tmp")
        settings.CRAWL4AI_PROMPT_FILE = "prompt.txt"
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.get_settings", lambda: settings
        )
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.read_file_content", lambda _path: "Content: {{CONTENT}}"
        )
        openai_schema = {"schema": True}
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.create_openai_schema_from_notion_database",
            lambda _schema, _add: openai_schema,
        )

        mock_openai_client.get_structured_response.return_value = {"title": "ok"}

        result = service._extract_with_crawl4ai_plus_gpt(
            "https://example.com/job",
            sample_notion_schema,
            "gpt-4o",
        )

        assert result == {"title": "ok"}
        mock_url_cache.get_cached_content.assert_called_once_with("https://example.com/job")
        mock_url_cache.cache_content.assert_not_called()
        mock_openai_client.get_structured_response.assert_called_once_with(
            sys_prompt=None,
            user_prompt="Content: cached markdown",
            model_name="gpt-4o",
            schema=openai_schema,
            use_web_search=False,
        )

    def test_extract_with_crawl4ai_plus_gpt_caches_new_content(
        self,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        mock_url_cache: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify new content is crawled and cached when not already stored."""
        service = ExtractorService(mock_openai_client, mock_notion_service)
        service.url_cache = mock_url_cache
        mock_url_cache.get_cached_content.return_value = None

        # Patch asyncio.run to return mocked crawl content
        def fake_run(coro: Any) -> str:
            coro.close()
            return "fetched markdown"

        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.asyncio.run",
            fake_run,
        )

        settings = MagicMock()
        settings.PROMPTS_DIRECTORY = Path("tmp")
        settings.CRAWL4AI_PROMPT_FILE = "prompt.txt"
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.get_settings", lambda: settings
        )
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.read_file_content", lambda _path: "Content: {{CONTENT}}"
        )
        openai_schema = {"schema": True}
        monkeypatch.setattr(
            "src.metadata_extraction.extractor_service.create_openai_schema_from_notion_database",
            lambda _schema, _add: openai_schema,
        )

        mock_openai_client.get_structured_response.return_value = {"title": "ok"}

        result = service._extract_with_crawl4ai_plus_gpt(
            "https://example.com/job",
            sample_notion_schema,
            "gpt-4o",
        )

        assert result == {"title": "ok"}
        mock_url_cache.get_cached_content.assert_called_once_with("https://example.com/job")
        mock_url_cache.cache_content.assert_called_once_with("https://example.com/job", "fetched markdown")
        mock_openai_client.get_structured_response.assert_called_once_with(
            sys_prompt=None,
            user_prompt="Content: fetched markdown",
            model_name="gpt-4o",
            schema=openai_schema,
            use_web_search=False,
        )
