"""Tests for the ExtractorService class."""

from collections.abc import Generator
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
