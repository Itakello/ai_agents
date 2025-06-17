"""Tests for the NotionService class."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

from src.common.models import NotionPage
from src.common.notion_service import NotionAPIError, NotionService


@pytest.fixture
def mock_client() -> Generator[MagicMock, None, None]:
    """Create a mock NotionClient that always returns a valid database dict and page dict."""
    with patch("src.common.notion_service.NotionClient") as mock:
        mock_instance = mock.return_value
        # Always return a valid Notion database schema
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": "test_database_id",
            "title": [{"plain_text": "Test Database", "type": "text"}],
            "properties": {
                "Title": {
                    "id": "title",
                    "type": "title",
                    "name": "Title",
                },
                "Company": {
                    "id": "company",
                    "type": "rich_text",
                    "name": "Company",
                },
                "Job URL": {
                    "id": "job_url",
                    "type": "url",
                    "name": "Job URL",
                },
                "Resume": {
                    "id": "resume",
                    "type": "files",
                    "name": "Resume",
                },
            },
        }
        # Always return a valid Notion page for retrieve and update
        valid_page = {
            "object": "page",
            "id": "test_page_id",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "archived": False,
            "properties": {
                "Title": {
                    "id": "title",
                    "type": "title",
                    "title": [{"type": "text", "plain_text": "Test Page", "text": {"content": "Test Page"}}],
                },
                "Company": {
                    "id": "company",
                    "type": "rich_text",
                    "rich_text": [{"type": "text", "plain_text": "Test Company", "text": {"content": "Test Company"}}],
                },
                "Job URL": {
                    "id": "job_url",
                    "type": "url",
                    "url": "https://example.com/job",
                },
                "Resume": {
                    "id": "resume",
                    "type": "files",
                    "files": [],
                },
            },
        }
        mock_instance.pages.retrieve.return_value = valid_page
        mock_instance.pages.update.return_value = valid_page
        yield mock


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
        result = service.get_page(page_id)

        # Assert
        mock_instance.pages.retrieve.assert_called_once_with(page_id=page_id)
        assert isinstance(result, NotionPage)
        assert result.object == "page"
        assert result.id == "test_page_id"
        assert result.title_text() == "Test Page"

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
            service.get_page(page_id)
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
        assert isinstance(result, NotionPage)
        assert result.id == "test_page_id"
        assert result.object == "page"

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
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "title": [{"plain_text": "Test Database", "type": "text"}],
            "properties": {
                "Title": {
                    "id": "title",
                    "type": "title",
                    "name": "Title",
                },
                "Company": {
                    "id": "company",
                    "type": "rich_text",
                    "name": "Company",
                },
                "Job URL": {
                    "id": "job_url",
                    "type": "url",
                    "name": "Job URL",
                },
                "Resume": {
                    "id": "resume",
                    "type": "files",
                    "name": "Resume",
                },
            },
        }
        service = NotionService(api_key=api_key, database_id=database_id, client=mock_instance)
        # Reset the mock to clear the initialization call
        mock_instance.databases.retrieve.reset_mock()
        # Act
        result = service.get_database_schema()
        # Assert
        mock_instance.databases.retrieve.assert_called_once_with(database_id=database_id)
        assert isinstance(result, dict)
        assert "Title" in result
        assert "Company" in result
        assert "Job URL" in result
        assert "Resume" in result

    def test_get_database_schema_error(self, mock_client: MagicMock) -> None:
        """Test error handling when retrieving database schema fails."""
        # Arrange
        api_key = "test_api_key"
        database_id = "test_database_id"
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.side_effect = Exception("Test error")
        # Act & Assert
        with pytest.raises(NotionAPIError) as exc_info:
            NotionService(api_key=api_key, database_id=database_id, client=mock_instance)
        assert "Failed to fetch database schema" in str(exc_info.value)

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
        assert isinstance(result, NotionPage)
        assert result.id == "test_page_id"

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
        assert isinstance(result, NotionPage)
        assert result.id == "test_page_id"

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
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "title": [{"type": "text", "text": {"content": "Database"}, "plain_text": "Database"}],
            "properties": {
                "Job Title": {"id": "title", "type": "title", "name": "Job Title"},
                "Company Website": {"id": "url", "type": "url", "name": "Company Website"},
                "Status": {"id": "stat", "type": "select", "name": "Status"},
            },
        }

        # Mock query to return no existing pages
        mock_instance.databases.query.return_value = {"results": []}

        # Mock page creation
        mock_instance.pages.create.return_value = {"id": "new_page_id"}

        url = "https://example.com/job"
        extracted_data = {"Job Title": "Software Engineer"}

        # Act
        service.save_or_update_extracted_data(url, extracted_data)

        # Assert
        mock_instance.databases.query.assert_called_once()
        mock_instance.pages.create.assert_called_once()

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

    def test_upload_file_to_page_property_success(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test successful file upload to Notion files property."""
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume PDF"
        file_path = tmp_path / "test_resume.pdf"
        file_path.write_bytes(b"dummy content")
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        # Mock schema with files property
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "title": [{"type": "text", "text": {"content": "Database"}, "plain_text": "Database"}],
            "properties": {
                property_name: {"id": "files", "type": "files", "name": property_name},
            },
        }
        # Patch requests.post for S3 upload
        with patch("src.common.notion_service.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status.return_value = None
            # Patch Notion client request for file upload object
            with patch.object(
                service.client, "request", return_value={"id": "fileid", "upload_url": "https://fake.s3/upload"}
            ) as mock_request:
                with patch.object(service, "update_page_property") as mock_update_page_property:
                    service.upload_file_to_page_property(file_path, page_id, property_name)
                    mock_request.assert_called_once_with(
                        path="file_uploads", method="POST", body={"name": file_path.name, "type": "file"}
                    )
                    mock_post.assert_called_once()
                    mock_update_page_property.assert_called_once_with(
                        page_id,
                        property_name,
                        {"files": [{"type": "file_upload", "file_upload": {"id": "fileid"}, "name": file_path.name}]},
                    )

    def test_upload_file_to_page_property_file_not_found(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test error if file does not exist."""
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume PDF"
        file_path = tmp_path / "nonexistent.pdf"
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "properties": {
                property_name: {"id": "files", "type": "files"},
            },
        }
        with pytest.raises(NotionAPIError, match="File does not exist"):
            service.upload_file_to_page_property(file_path, page_id, property_name)

    def test_upload_file_to_page_property_wrong_property_type(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test error if property type is not 'files'."""
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume PDF"
        file_path = tmp_path / "test_resume.pdf"
        file_path.write_bytes(b"dummy content")
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "title": [{"type": "text", "text": {"content": "Database"}, "plain_text": "Database"}],
            "properties": {
                property_name: {"id": "url", "type": "url", "name": property_name},
            },
        }
        with pytest.raises(NotionAPIError, match="only supports 'files' properties"):
            service.upload_file_to_page_property(file_path, page_id, property_name)

    def test_upload_file_to_page_property_notion_api_error(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test Notion API error during file upload object creation."""
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume PDF"
        file_path = tmp_path / "test_resume.pdf"
        file_path.write_bytes(b"dummy content")
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "title": [{"type": "text", "text": {"content": "Database"}, "plain_text": "Database"}],
            "properties": {
                property_name: {"id": "files", "type": "files", "name": property_name},
            },
        }
        # Patch client.request to raise error
        with patch.object(service.client, "request", side_effect=Exception("notion error")):
            with patch("src.common.notion_service.requests.post"):
                with pytest.raises(
                    NotionAPIError, match="File upload failed: Failed to create Notion file upload object"
                ):
                    service.upload_file_to_page_property(file_path, page_id, property_name)

    def test_upload_file_to_page_property_s3_upload_error(self, mock_client: MagicMock, tmp_path: Path) -> None:
        """Test error during S3 upload step."""
        api_key = "test_api_key"
        database_id = "test_database_id"
        page_id = "test_page_id"
        property_name = "Resume PDF"
        file_path = tmp_path / "test_resume.pdf"
        file_path.write_bytes(b"dummy content")
        service = NotionService(api_key=api_key, database_id=database_id)
        mock_instance = mock_client.return_value
        mock_instance.databases.retrieve.return_value = {
            "object": "database",
            "id": database_id,
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "title": [{"type": "text", "text": {"content": "Database"}, "plain_text": "Database"}],
            "properties": {
                property_name: {"id": "files", "type": "files", "name": property_name},
            },
        }
        with patch.object(
            service.client, "request", return_value={"id": "fileid", "upload_url": "https://fake.s3/upload"}
        ):
            with patch("src.common.notion_service.requests.post") as mock_post:
                mock_post.return_value.raise_for_status.side_effect = Exception("s3 error")
                with pytest.raises(NotionAPIError, match="File upload failed: Failed to upload file contents"):
                    service.upload_file_to_page_property(file_path, page_id, property_name)
