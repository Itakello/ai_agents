"""Tests for the NotionService class."""

import os
from collections.abc import Generator
from pathlib import Path  # Moved import here
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from src.common.notion_service import NotionAPIError, NotionService


class TestNotionService:
    """Test suite for the NotionService class."""

    @pytest.fixture(autouse=True)
    def mock_environment(self) -> Generator:
        """Mock environment variables required for testing."""
        env_vars = {
            "OPENAI_API_KEY": "test_openai_key",
            "NOTION_API_KEY": "test_notion_key",
            "NOTION_DATABASE_ID": "test_database_id",
            "MASTER_RESUME_PATH": "/fake/path/to/resume.tex",
        }
        with mock.patch.dict(os.environ, env_vars):
            yield

    @pytest.fixture
    def mock_client(self) -> Generator[MagicMock]:
        """Create a mock Notion client with realistic response structures from API docs."""
        with patch("src.common.notion_service.NotionClient") as mock_client_class:
            # Real Notion API page response structure
            default_page_response = {
                "object": "page",
                "id": "test_page_id",
                "created_time": "2022-10-24T22:54:00.000Z",
                "last_edited_time": "2023-03-08T18:25:00.000Z",
                "created_by": {
                    "object": "user",
                    "id": "c2f20311-9e54-4d11-8c79-7398424ae41e",
                },
                "last_edited_by": {
                    "object": "user",
                    "id": "9188c6a5-7381-452f-b3dc-d4865aa89bdf",
                },
                "cover": None,
                "icon": {"type": "emoji", "emoji": "🐞"},
                "parent": {"type": "database_id", "database_id": "test_database_id"},
                "archived": False,
                "url": "https://www.notion.so/Test-Page-testpageid",
                "properties": {
                    "Title": {
                        "id": "title",
                        "type": "title",
                        "title": [
                            {
                                "type": "text",
                                "text": {"content": "Test Page", "link": None},
                                "annotations": {
                                    "bold": False,
                                    "italic": False,
                                    "strikethrough": False,
                                    "underline": False,
                                    "code": False,
                                    "color": "default",
                                },
                                "plain_text": "Test Page",
                                "href": None,
                            }
                        ],
                    }
                },
            }

            # Real Notion API database response structure with properties schema
            default_database_response = {
                "object": "database",
                "id": "test_database_id",
                "created_time": "2022-10-24T22:54:00.000Z",
                "last_edited_time": "2023-03-08T18:25:00.000Z",
                "title": [{"type": "text", "text": {"content": "Job Applications"}}],
                "properties": {
                    "Job Title": {"id": "title", "type": "title"},
                    "Company": {"id": "comp", "type": "rich_text"},
                    "Status": {
                        "id": "stat",
                        "type": "status",
                        "status": {
                            "options": [
                                {"name": "Not started", "id": "1", "color": "default"},
                                {"name": "In progress", "id": "2", "color": "blue"},
                                {"name": "Done", "id": "3", "color": "green"},
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
                            ]
                        },
                    },
                },
            }

            # Set up mock client instance
            mock_instance = MagicMock()
            mock_instance.pages.retrieve.return_value = default_page_response
            mock_instance.pages.update.return_value = default_page_response
            mock_instance.databases.retrieve.return_value = default_database_response
            mock_client_class.return_value = mock_instance
            yield mock_client_class

    def test_init(self, mock_client: MagicMock) -> None:
        """Test that the client is initialized with the correct API key and database ID."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"

        # Act
        service = NotionService(api_key=api_key, database_id=database_id)

        # Assert
        mock_client.assert_called_once_with(auth=api_key)
        assert service.database_id == database_id

    def test_get_page_content_success(self, mock_client: MagicMock) -> None:
        """Test successful retrieval of page content."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"

        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value

        # Act
        result = service.get_page_content(page_id)

        # Assert
        mock_instance.pages.retrieve.assert_called_once_with(page_id=page_id)
        assert result["object"] == "page"
        assert result["id"] == "test_page_id"
        assert result["properties"]["Title"]["title"][0]["text"]["content"] == "Test Page"

    def test_get_page_content_error(self, mock_client: MagicMock) -> None:
        """Test error handling when retrieving page content fails."""
        # Arrange
        api_key: str = "test_api_key"
        database_id: str = "test_database_id"
        page_id: str = "test_page_id"

        # Configure the mock to raise an error
        mock_instance = mock_client.return_value
        mock_instance.pages.retrieve.side_effect = Exception("Test error")

        service = NotionService(api_key=api_key, database_id=database_id)

        # Act & Assert
        with pytest.raises(NotionAPIError) as exc_info:
            service.get_page_content(page_id)
        assert f"Failed to fetch page {page_id}:" in str(exc_info.value)

    def test_update_page_property_success(self, mock_client: MagicMock) -> None:
        """Test successful update of a page property."""
        # Arrange
        api_key: str = "test_api_key"
        database_id: str = "test_database_id"
        page_id: str = "test_page_id"
        property_name: str = "Status"
        property_value: dict[str, Any] = {"status": {"name": "In Progress"}}

        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value

        # Act
        result = service.update_page_property(page_id, property_name, property_value)

        # Assert
        mock_instance.pages.update.assert_called_once_with(page_id=page_id, properties={property_name: property_value})
        # Verify the response follows real Notion API structure
        assert result["object"] == "page"
        assert result["id"] == "test_page_id"
        assert "properties" in result

    def test_update_page_property_error(self, mock_client: MagicMock) -> None:
        """Test error handling when updating a page property fails."""
        # Arrange
        api_key: str = "test_api_key"
        database_id: str = "test_database_id"
        page_id: str = "test_page_id"
        property_name: str = "Status"
        property_value: dict[str, Any] = {"status": {"name": "In Progress"}}

        # Configure the mock to raise an error
        mock_instance = mock_client.return_value
        mock_instance.pages.update.side_effect = Exception("Test error")

        service = NotionService(api_key=api_key, database_id=database_id)

        # Act & Assert
        with pytest.raises(NotionAPIError) as exc_info:
            service.update_page_property(page_id, property_name, property_value)
        assert "Failed to update property" in str(exc_info.value)

    def test_get_database_schema_success(self, mock_client: MagicMock) -> None:
        """Test successful retrieval of database schema."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"

        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value

        # Act
        result = service.get_database_schema()

        # Assert
        mock_instance.databases.retrieve.assert_called_once_with(database_id=database_id)
        assert "Job Title" in result
        assert result["Job Title"]["type"] == "title"
        assert "Status" in result
        assert result["Status"]["type"] == "status"
        assert "Skills" in result
        assert result["Skills"]["type"] == "multi_select"

    def test_get_database_schema_error(self, mock_client: MagicMock) -> None:
        """Test error handling when retrieving database schema fails."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"

        # Configure the mock to raise an error
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.side_effect = Exception("Test error")

        service = NotionService(api_key=api_key, database_id=database_id)

        # Act & Assert
        with pytest.raises(NotionAPIError) as exc_info:
            service.get_database_schema()
        assert f"Failed to fetch database schema for {database_id}:" in str(exc_info.value)

    def test_update_page_properties_success_with_properties_wrapper(self, mock_client: MagicMock) -> None:
        """Test successful update of multiple page properties with properties wrapper."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        properties_update = {
            "properties": {
                "Job Title": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
                "Salary": {"number": 75000.0},
                "Remote": {"checkbox": True},
            }
        }

        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value

        # Act
        result = service.update_page_properties(page_id, properties_update)

        # Assert
        expected_properties = properties_update["properties"]
        mock_instance.pages.update.assert_called_once_with(page_id=page_id, properties=expected_properties)
        assert result["object"] == "page"
        assert result["id"] == "test_page_id"

    def test_update_page_properties_success_without_wrapper(self, mock_client: MagicMock) -> None:
        """Test successful update of multiple page properties without properties wrapper."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        properties_update = {
            "Job Title": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
            "Salary": {"number": 75000.0},
            "Remote": {"checkbox": True},
        }

        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value

        # Act
        result = service.update_page_properties(page_id, properties_update)

        # Assert
        mock_instance.pages.update.assert_called_once_with(page_id=page_id, properties=properties_update)
        assert result["object"] == "page"
        assert result["id"] == "test_page_id"

    def test_update_page_properties_error(self, mock_client: MagicMock) -> None:
        """Test error handling when updating multiple page properties fails."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        properties_update = {
            "Job Title": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
            "Salary": {"number": 75000.0},
        }

        # Configure the mock to raise an error
        mock_instance = mock_client.return_value
        mock_instance.pages.update.side_effect = Exception("Test error")

        service = NotionService(api_key=api_key, database_id=database_id)

        # Act & Assert
        with pytest.raises(NotionAPIError) as exc_info:
            service.update_page_properties(page_id, properties_update)
        assert f"Failed to update properties on page {page_id}:" in str(exc_info.value)

    def test_save_or_update_extracted_data_auto_detects_url_property(self, mock_client: MagicMock) -> None:
        """Test that save_or_update_extracted_data auto-detects URL property name."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value

        # Mock database schema with "Company Website" as URL property
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "properties": {
                "Job Title": {"id": "title", "type": "title"},
                "Company Website": {"id": "url", "type": "url"},
                "Status": {"id": "stat", "type": "select"},
            },
        }

        # Mock query to return no existing pages
        mock_instance.databases.query.return_value = {"results": []}

        # Mock page creation
        mock_instance.pages.create.return_value = {"id": "new_page_id"}

        url = "https://example.com/job"
        extracted_data = {"Job Title": "Software Engineer"}

        # Act
        result = service.save_or_update_extracted_data(url, extracted_data)

        # Assert
        # Verify that query was called with the correct URL property name
        mock_instance.databases.query.assert_called_once()
        query_args = mock_instance.databases.query.call_args
        assert query_args[1]["filter"]["property"] == "Job URL"
        assert result == {"id": "new_page_id"}

    def test_upload_file_to_page_property_url(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test upload_file_to_page_property stores local file path in a URL property."""

        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume PDF"
        file_path = tmp_path / "test_resume.pdf"
        file_path.write_text("dummy content")
        # Mock schema with URL property
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "properties": {
                property_name: {"id": "url", "type": "url"},
            },
        }
        # Act
        result = service.upload_file_to_page_property(file_path, page_id, property_name)
        # Assert
        mock_instance.pages.update.assert_called_once_with(
            page_id=page_id, properties={property_name: {"url": str(file_path)}}
        )
        assert result == str(file_path)

    def test_upload_file_to_page_property_rich_text(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test upload_file_to_page_property stores local file path in a rich_text property."""

        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume Path"
        file_path = tmp_path / "test_resume.pdf"
        file_path.write_text("dummy content")
        # Mock schema with rich_text property
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "properties": {
                property_name: {"id": "rt", "type": "rich_text"},
            },
        }
        # Act
        result = service.upload_file_to_page_property(file_path, page_id, property_name)
        # Assert
        mock_instance.pages.update.assert_called_once_with(
            page_id=page_id, properties={property_name: {"rich_text": [{"text": {"content": str(file_path)}}]}}
        )
        assert result == str(file_path)

    def test_upload_file_to_page_property_handles_error(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test upload_file_to_page_property returns None on error."""

        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume PDF"
        file_path = tmp_path / "test_resume.pdf"
        file_path.write_text("dummy content")
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        # Simulate error in update_page_property
        mock_instance.databases.retrieve.side_effect = Exception("Schema error")
        with pytest.raises(NotionAPIError, match="Failed to fetch database schema"):
            service.upload_file_to_page_property(file_path, page_id, property_name)
