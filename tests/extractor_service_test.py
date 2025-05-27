"""Tests for the ExtractorService class."""

import json
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from src.metadata_extraction.extractor_service import ExtractorService, ExtractorServiceError


class TestExtractorService:
    """Test suite for the ExtractorService class."""

    @pytest.fixture
    def mock_openai_client(self) -> Generator[MagicMock, None, None]:
        """Create a mock OpenAI client."""
        mock_client = MagicMock()
        mock_client.get_response.return_value = '{"job_title": "Software Engineer", "company": "Tech Corp"}'
        yield mock_client

    @pytest.fixture
    def mock_notion_service(self) -> Generator[MagicMock, None, None]:
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

    def test_extract_metadata_success(
        self,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        sample_job_description: str,
    ) -> None:
        """Test successful metadata extraction."""
        # Arrange
        expected_response = {
            "Job Title": "Software Engineer",
            "Company": "Tech Corp",
            "Status": "Applied",
            "Salary": 100000,
            "Remote": True,
            "Skills": ["Python", "JavaScript", "React"],
            "Contact Email": "jobs@techcorp.com",
            "Company Website": "https://techcorp.com",
        }

        mock_openai_client.get_response.return_value = json.dumps(expected_response)

        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act
        result = service.extract_metadata_from_job_description(sample_job_description, sample_notion_schema)

        # Assert
        assert result == expected_response
        mock_openai_client.get_response.assert_called_once()

        # Verify the prompt construction
        call_args = mock_openai_client.get_response.call_args
        assert call_args[1]["model_name"] == "gpt-4-1106-preview"
        prompt = call_args[1]["user_prompt"]
        assert "Software Engineer Position at Tech Corp" in prompt
        assert "Job Title" in prompt
        assert "Company" in prompt
        assert "JSON Schema for validation" in prompt

    def test_extract_metadata_empty_job_description(
        self, mock_openai_client: MagicMock, mock_notion_service: MagicMock, sample_notion_schema: dict[str, Any]
    ) -> None:
        """Test error handling for empty job description."""
        # Arrange
        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act & Assert
        with pytest.raises(ExtractorServiceError) as exc_info:
            service.extract_metadata_from_job_description("", sample_notion_schema)
        assert "Job description text cannot be empty" in str(exc_info.value)

        with pytest.raises(ExtractorServiceError) as exc_info:
            service.extract_metadata_from_job_description("   ", sample_notion_schema)
        assert "Job description text cannot be empty" in str(exc_info.value)

    def test_extract_metadata_empty_schema(
        self, mock_openai_client: MagicMock, mock_notion_service: MagicMock, sample_job_description: str
    ) -> None:
        """Test error handling for empty schema."""
        # Arrange
        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act & Assert
        with pytest.raises(ExtractorServiceError) as exc_info:
            service.extract_metadata_from_job_description(sample_job_description, {})
        assert "Notion database schema cannot be empty" in str(exc_info.value)

    def test_extract_metadata_invalid_json_response(
        self,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        sample_job_description: str,
    ) -> None:
        """Test error handling for invalid JSON response from LLM."""
        # Arrange
        mock_openai_client.get_response.return_value = "This is not valid JSON"
        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act & Assert
        with pytest.raises(ExtractorServiceError) as exc_info:
            service.extract_metadata_from_job_description(sample_job_description, sample_notion_schema)
        assert "Failed to parse LLM response as JSON" in str(exc_info.value)

    def test_extract_metadata_non_object_response(
        self,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        sample_job_description: str,
    ) -> None:
        """Test error handling for non-object JSON response."""
        # Arrange
        mock_openai_client.get_response.return_value = '["not", "an", "object"]'
        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act & Assert
        with pytest.raises(ExtractorServiceError) as exc_info:
            service.extract_metadata_from_job_description(sample_job_description, sample_notion_schema)
        assert "LLM response is not a valid JSON object" in str(exc_info.value)

    def test_extract_metadata_openai_client_error(
        self,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        sample_job_description: str,
    ) -> None:
        """Test error handling when OpenAI client raises an exception."""
        # Arrange
        mock_openai_client.get_response.side_effect = Exception("OpenAI API Error")
        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act & Assert
        with pytest.raises(ExtractorServiceError) as exc_info:
            service.extract_metadata_from_job_description(sample_job_description, sample_notion_schema)
        assert "Error during metadata extraction" in str(exc_info.value)

    @patch("src.metadata_extraction.extractor_service.create_openai_schema_from_notion_database")
    def test_build_extraction_prompt(
        self,
        mock_create_schema: MagicMock,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        sample_notion_schema: dict[str, Any],
        sample_job_description: str,
    ) -> None:
        """Test the prompt building functionality."""
        # Arrange
        expected_openai_schema = {
            "type": "object",
            "properties": {
                "Job Title": {"type": "string"},
                "Skills": {"type": "array", "items": {"type": "string", "enum": ["Python", "JavaScript", "React"]}},
                "Salary": {"type": "number"},
            },
            "required": [],
            "additionalProperties": False,
        }
        mock_create_schema.return_value = expected_openai_schema
        mock_openai_client.get_response.return_value = '{"Job Title": "Test"}'

        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act
        service.extract_metadata_from_job_description(sample_job_description, sample_notion_schema)

        # Assert
        mock_create_schema.assert_called_once_with(sample_notion_schema)
        call_args = mock_openai_client.get_response.call_args
        prompt = call_args[1]["user_prompt"]

        # Verify prompt contains key elements
        assert "You are an expert at analyzing job descriptions" in prompt
        assert sample_job_description in prompt
        assert "Job Title: string" in prompt
        assert "Skills: array (array of options: Python, JavaScript, React)" in prompt
        assert "Salary: number" in prompt
        assert "JSON Schema for validation" in prompt
        assert json.dumps(expected_openai_schema, indent=2) in prompt

    def test_extract_metadata_with_minimal_schema(
        self, mock_openai_client: MagicMock, mock_notion_service: MagicMock, sample_job_description: str
    ) -> None:
        """Test extraction with a minimal schema containing only basic types."""
        # Arrange
        minimal_schema = {
            "Job Title": {"id": "title", "type": "title"},
            "Notes": {"id": "notes", "type": "rich_text"},
        }

        expected_response = {"Job Title": "Software Engineer", "Notes": "Interesting position"}
        mock_openai_client.get_response.return_value = json.dumps(expected_response)

        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act
        result = service.extract_metadata_from_job_description(sample_job_description, minimal_schema)

        # Assert
        assert result == expected_response
        mock_openai_client.get_response.assert_called_once()

    def test_extract_metadata_schema_filtering(
        self, mock_openai_client: MagicMock, mock_notion_service: MagicMock, sample_job_description: str
    ) -> None:
        """Test that read-only properties are filtered out from the schema."""
        # Arrange
        schema_with_readonly = {
            "Job Title": {"id": "title", "type": "title"},
            "Created Time": {"id": "created", "type": "created_time"},
            "Formula Field": {"id": "formula", "type": "formula"},
            "Rollup Field": {"id": "rollup", "type": "rollup"},
        }

        expected_response = {"Job Title": "Software Engineer"}
        mock_openai_client.get_response.return_value = json.dumps(expected_response)

        service = ExtractorService(mock_openai_client, mock_notion_service)

        # Act
        result = service.extract_metadata_from_job_description(sample_job_description, schema_with_readonly)

        # Assert
        assert result == expected_response
        call_args = mock_openai_client.get_response.call_args
        prompt = call_args[1]["user_prompt"]

        # Verify that read-only fields are not included in the prompt
        assert "Job Title" in prompt
        assert "Created Time" not in prompt
        assert "Formula Field" not in prompt
        assert "Rollup Field" not in prompt
