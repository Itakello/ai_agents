"""Tests for the NotionSyncService class."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.exceptions.notion_exceptions import NotionAPIError
from src.common.models.notion_database import NotionDatabase
from src.common.models.notion_page import NotionPage
from src.common.services.notion_sync_service import NotionSyncService


@pytest.fixture
def mock_api_service() -> MagicMock:
    """Create a mock NotionAPIService."""
    service = MagicMock()
    # Provide a minimal yet valid database schema so that schema validation in
    # ``NotionSyncService`` passes during tests.
    minimal_db_payload: dict[str, Any] = {
        "object": "database",
        "id": "test-db-id",
        "title": [],
        "properties": {
            "Title": {"id": "prop_title", "type": "title", "name": "Title", "title": []},
            "Job URL": {"id": "prop_url", "type": "url", "name": "Job URL", "url": {}},
        },
    }

    service.get_database = AsyncMock(return_value=NotionDatabase.model_validate(minimal_db_payload))
    # ``_ensure_required_properties`` may attempt to update the database – we
    # simply echo back the same (already valid) payload in our mock.
    service.update_database = AsyncMock(return_value=NotionDatabase.model_validate(minimal_db_payload))
    service.get_page = AsyncMock()
    service.update_page = AsyncMock()
    service.create_page = AsyncMock()
    service.find_page_by_url = AsyncMock()
    service.query_database = AsyncMock()
    return service


@pytest.fixture
def mock_file_service() -> MagicMock:
    """Create a mock NotionFileService."""
    service = MagicMock()
    service.upload_file = AsyncMock()
    return service


@pytest.fixture
def sync_service(mock_api_service: MagicMock, mock_file_service: MagicMock) -> NotionSyncService:
    """Create a NotionSyncService instance with mock services."""
    return NotionSyncService(api_service=mock_api_service, file_service=mock_file_service)


@pytest.mark.asyncio
async def test_get_database(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test getting a database."""
    mock_data: dict[str, Any] = {
        "object": "database",
        "id": "test-db-id",
        "title": [{"type": "text", "text": {"content": "Test Database"}, "plain_text": "Test Database"}],
        "properties": {
            "Name": {"id": "prop_name", "type": "title", "name": "Name"},
            "Description": {"id": "prop_desc", "type": "rich_text", "name": "Description"},
        },
    }
    mock_api_service.get_database.return_value = NotionDatabase.model_validate(mock_data)

    result = await sync_service.get_database("test-db-id")
    assert isinstance(result, NotionDatabase)
    assert result.id == "test-db-id"
    assert result.title[0].plain_text == "Test Database"


@pytest.mark.asyncio
async def test_get_page(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test getting a page."""
    mock_data: dict[str, Any] = {
        "object": "page",
        "id": "test-page-id",
        "title": [{"type": "text", "text": {"content": "Test Page"}, "plain_text": "Test Page"}],
        "properties": {
            "Name": {
                "id": "prop_name",
                "type": "title",
                "name": "Name",
                "title": [{"type": "text", "text": {"content": "Test Page"}, "plain_text": "Test Page"}],
            },
        },
    }
    mock_api_service.get_page.return_value = NotionPage.model_validate(mock_data)

    result = await sync_service.get_page("test-page-id")
    assert isinstance(result, NotionPage)
    assert result.id == "test-page-id"
    assert result.title[0].plain_text == "Test Page"


@pytest.mark.asyncio
async def test_update_page(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test updating a page."""
    mock_data: dict[str, Any] = {
        "object": "page",
        "id": "test-page-id",
        "title": [{"type": "text", "text": {"content": "Updated Page"}, "plain_text": "Updated Page"}],
        "properties": {
            "Name": {
                "id": "prop_name",
                "type": "title",
                "name": "Name",
                "title": [{"type": "text", "text": {"content": "Updated Page"}, "plain_text": "Updated Page"}],
            },
        },
    }
    mock_api_service.update_page.return_value = NotionPage.model_validate(mock_data)

    properties = {"Name": {"title": [{"text": {"content": "Updated Page"}}]}}
    result = await sync_service.update_page("test-page-id", properties)
    assert isinstance(result, NotionPage)
    assert result.id == "test-page-id"
    assert result.title[0].plain_text == "Updated Page"


@pytest.mark.asyncio
async def test_create_page(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test creating a page."""
    mock_data: dict[str, Any] = {
        "object": "page",
        "id": "new-page-id",
        "title": [{"type": "text", "text": {"content": "New Page"}, "plain_text": "New Page"}],
        "properties": {
            "Name": {
                "id": "prop_name",
                "type": "title",
                "name": "Name",
                "title": [{"type": "text", "text": {"content": "New Page"}, "plain_text": "New Page"}],
            },
            "URL": {"id": "prop_url", "type": "url", "name": "URL", "url": "https://example.com"},
        },
    }
    mock_api_service.create_page.return_value = NotionPage.model_validate(mock_data)

    properties = {"Name": {"title": [{"text": {"content": "New Page"}}]}}
    result = await sync_service.create_page("test-db-id", properties)
    assert isinstance(result, NotionPage)
    assert result.id == "new-page-id"
    assert result.title[0].plain_text == "New Page"


@pytest.mark.asyncio
async def test_upload_file_to_page(
    sync_service: NotionSyncService, mock_file_service: MagicMock, mock_api_service: MagicMock, tmp_path: Path
) -> None:
    """Test uploading a file to a page."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Test content")

    mock_data: dict[str, Any] = {
        "object": "page",
        "id": "test-page-id",
        "title": [{"type": "text", "text": {"content": "Test Page"}, "plain_text": "Test Page"}],
        "properties": {
            "Name": {
                "id": "prop_name",
                "type": "title",
                "name": "Name",
                "title": [{"type": "text", "text": {"content": "Test Page"}, "plain_text": "Test Page"}],
            },
        },
    }
    mock_api_service.get_page.return_value = NotionPage.model_validate(mock_data)
    mock_api_service.update_page.return_value = NotionPage.model_validate(mock_data)

    await sync_service.upload_file_to_page(str(file_path), "test-page-id", "test-property")
    mock_file_service.upload_file.assert_called_once_with(str(file_path), "test-page-id", "test-property")


@pytest.mark.asyncio
async def test_find_page_by_url(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test finding a page by URL."""
    mock_data: dict[str, Any] = {
        "object": "page",
        "id": "test-page-id",
        "title": [{"type": "text", "text": {"content": "Test Page"}, "plain_text": "Test Page"}],
        "properties": {
            "Name": {
                "id": "prop_name",
                "type": "title",
                "name": "Name",
                "title": [{"type": "text", "text": {"content": "Test Page"}, "plain_text": "Test Page"}],
            },
            "URL": {"id": "prop_url", "type": "url", "name": "URL", "url": "https://example.com"},
        },
    }
    mock_api_service.query_database.return_value = [NotionPage.model_validate(mock_data)]

    result = await sync_service.query_database("test-db-id", {"URL": {"url": {"equals": "https://example.com"}}})
    assert len(result) == 1
    assert result[0].id == "test-page-id"
    assert result[0].title[0].plain_text == "Test Page"


@pytest.mark.asyncio
async def test_save_or_update_extracted_data_new_page(
    sync_service: NotionSyncService, mock_api_service: MagicMock
) -> None:
    """Test saving extracted data for a new page."""
    mock_data: dict[str, Any] = {
        "object": "page",
        "id": "new-page-id",
        "title": [{"type": "text", "text": {"content": "New Page"}, "plain_text": "New Page"}],
        "properties": {
            "Name": {
                "id": "prop_name",
                "type": "title",
                "name": "Name",
                "title": [{"type": "text", "text": {"content": "New Page"}, "plain_text": "New Page"}],
            },
            "URL": {"id": "prop_url", "type": "url", "name": "URL", "url": "https://example.com"},
        },
    }
    mock_api_service.query_database.return_value = []
    mock_api_service.create_page.return_value = NotionPage.model_validate(mock_data)

    extracted_data = {
        "Name": "New Page",
        "URL": "https://example.com",
    }
    result = await sync_service.save_or_update_extracted_data("test-db-id", "https://example.com", extracted_data)
    assert isinstance(result, NotionPage)
    assert result.id == "new-page-id"
    assert result.title[0].plain_text == "New Page"


@pytest.mark.asyncio
async def test_save_or_update_extracted_data_existing_page(
    sync_service: NotionSyncService, mock_api_service: MagicMock
) -> None:
    """Test updating extracted data for an existing page."""
    mock_data: dict[str, Any] = {
        "object": "page",
        "id": "test-page-id",
        "title": [{"type": "text", "text": {"content": "Updated Page"}, "plain_text": "Updated Page"}],
        "properties": {
            "Name": {
                "id": "prop_name",
                "type": "title",
                "name": "Name",
                "title": [{"type": "text", "text": {"content": "Updated Page"}, "plain_text": "Updated Page"}],
            },
            "URL": {"id": "prop_url", "type": "url", "name": "URL", "url": "https://example.com"},
        },
    }
    mock_api_service.query_database.return_value = [NotionPage.model_validate(mock_data)]
    mock_api_service.update_page.return_value = NotionPage.model_validate(mock_data)

    extracted_data = {
        "Name": "Updated Page",
        "URL": "https://example.com",
    }
    result = await sync_service.save_or_update_extracted_data("test-db-id", "https://example.com", extracted_data)
    assert isinstance(result, NotionPage)
    assert result.id == "test-page-id"
    assert result.title[0].plain_text == "Updated Page"


@pytest.mark.asyncio
async def test_get_database_error(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test error handling when getting a database."""
    mock_api_service.get_database.side_effect = NotionAPIError("API Error")

    with pytest.raises(NotionAPIError) as exc_info:
        await sync_service.get_database("test-db-id")
    assert "Failed to get database" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_page_error(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test error handling when getting a page."""
    mock_api_service.get_page.side_effect = NotionAPIError("API Error")

    with pytest.raises(NotionAPIError) as exc_info:
        await sync_service.get_page("test-page-id")
    assert "Failed to get page" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_page_error(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test error handling when updating a page."""
    mock_api_service.update_page.side_effect = NotionAPIError("API Error")

    with pytest.raises(NotionAPIError) as exc_info:
        await sync_service.update_page("test-page-id", {})
    assert "Failed to update page" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_page_error(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test error handling when creating a page."""
    mock_api_service.create_page.side_effect = NotionAPIError("API Error")

    with pytest.raises(NotionAPIError) as exc_info:
        await sync_service.create_page("test-db-id", {})
    assert "Failed to create page" in str(exc_info.value)


@pytest.mark.asyncio
async def test_find_page_by_url_error(sync_service: NotionSyncService, mock_api_service: MagicMock) -> None:
    """Test error handling when finding a page by URL."""
    mock_api_service.query_database.side_effect = NotionAPIError("API Error")

    with pytest.raises(NotionAPIError) as exc_info:
        await sync_service.query_database("test-db-id", {"URL": {"url": {"equals": "https://example.com"}}})
    assert "Failed to query database" in str(exc_info.value)


@pytest.mark.asyncio
async def test_save_or_update_extracted_data_error(
    sync_service: NotionSyncService, mock_api_service: MagicMock
) -> None:
    """Test error handling when saving or updating extracted data."""
    mock_api_service.query_database.side_effect = NotionAPIError("API Error")

    with pytest.raises(NotionAPIError) as exc_info:
        await sync_service.save_or_update_extracted_data("test-db-id", "https://example.com", {})
    assert "Failed to save or update extracted data" in str(exc_info.value)
