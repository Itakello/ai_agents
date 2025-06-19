"""Tests for the NotionAPIService class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.exceptions.notion_exceptions import NotionAPIError
from src.common.models import NotionDatabase, NotionPage
from src.common.services import NotionAPIService


@pytest.fixture
def mock_notion_client() -> MagicMock:
    """Create a mock Notion client."""
    client = MagicMock()
    client.databases.retrieve = AsyncMock()
    client.pages.retrieve = AsyncMock()
    client.pages.update = AsyncMock()
    client.databases.query = AsyncMock()
    client.pages.create = AsyncMock()
    return client


@pytest.fixture
def api_service(mock_notion_client: MagicMock) -> NotionAPIService:
    """Create a NotionAPIService instance with a mock client."""
    return NotionAPIService(api_key="test-api-key")


@pytest.mark.asyncio
async def test_get_database(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test getting a database."""
    mock_data = {
        "object": "database",
        "id": "test-db-id",
        "title": [{"type": "text", "text": {"content": "Test Database"}, "plain_text": "Test Database"}],
        "properties": {
            "Name": {"id": "prop_name", "type": "title", "name": "Name"},
            "Description": {"id": "prop_desc", "type": "rich_text", "name": "Description"},
        },
    }
    mock_notion_client.databases.retrieve = AsyncMock(return_value=mock_data)
    api_service.client = mock_notion_client

    result = await api_service.get_database("test-db-id")
    assert isinstance(result, NotionDatabase)
    assert result.id == "test-db-id"
    assert result.title[0].plain_text == "Test Database"
    assert "Name" in result.properties
    assert "Description" in result.properties


@pytest.mark.asyncio
async def test_get_page(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test getting a page."""
    mock_data = {
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
    mock_notion_client.pages.retrieve = AsyncMock(return_value=mock_data)
    api_service.client = mock_notion_client

    result = await api_service.get_page("test-page-id")
    assert isinstance(result, NotionPage)
    assert result.id == "test-page-id"
    assert result.title[0].plain_text == "Test Page"


@pytest.mark.asyncio
async def test_update_page(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test updating a page."""
    mock_data = {
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
    mock_notion_client.pages.update = AsyncMock(return_value=mock_data)
    api_service.client = mock_notion_client

    properties = {"Name": {"title": [{"text": {"content": "Updated Page"}}]}}
    result = await api_service.update_page("test-page-id", properties)
    assert isinstance(result, NotionPage)
    assert result.id == "test-page-id"
    assert result.title[0].plain_text == "Updated Page"


@pytest.mark.asyncio
async def test_create_page(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test creating a page."""
    mock_data = {
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
        },
    }
    mock_notion_client.pages.create = AsyncMock(return_value=mock_data)
    api_service.client = mock_notion_client

    properties = {"Name": {"title": [{"text": {"content": "New Page"}}]}}
    result = await api_service.create_page({"database_id": "test-db-id"}, properties)
    assert isinstance(result, NotionPage)
    assert result.id == "new-page-id"
    assert result.title[0].plain_text == "New Page"


@pytest.mark.asyncio
async def test_find_page_by_url(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test finding a page by URL."""
    mock_data = {
        "results": [
            {
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
        ]
    }
    mock_notion_client.databases.query = AsyncMock(return_value=mock_data)
    api_service.client = mock_notion_client

    result = await api_service.query_database("test-db-id", {"URL": {"url": {"equals": "https://example.com"}}})
    assert len(result) == 1
    assert result[0].id == "test-page-id"
    assert result[0].title[0].plain_text == "Test Page"


@pytest.mark.asyncio
async def test_get_database_error(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test error handling when getting a database."""
    mock_notion_client.databases.retrieve = AsyncMock(side_effect=Exception("API Error"))
    api_service.client = mock_notion_client

    with pytest.raises(NotionAPIError) as exc_info:
        await api_service.get_database("test-db-id")
    assert "Failed to get database" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_page_error(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test error handling when getting a page."""
    mock_notion_client.pages.retrieve = AsyncMock(side_effect=Exception("API Error"))
    api_service.client = mock_notion_client

    with pytest.raises(NotionAPIError) as exc_info:
        await api_service.get_page("test-page-id")
    assert "Failed to get page" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_page_error(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test error handling when updating a page."""
    mock_notion_client.pages.update = AsyncMock(side_effect=Exception("API Error"))
    api_service.client = mock_notion_client

    with pytest.raises(NotionAPIError) as exc_info:
        await api_service.update_page("test-page-id", {})
    assert "Failed to update page" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_page_error(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test error handling when creating a page."""
    mock_notion_client.pages.create = AsyncMock(side_effect=Exception("API Error"))
    api_service.client = mock_notion_client

    with pytest.raises(NotionAPIError) as exc_info:
        await api_service.create_page({"database_id": "test-db-id"}, {})
    assert "Failed to create page" in str(exc_info.value)


@pytest.mark.asyncio
async def test_find_page_by_url_error(api_service: NotionAPIService, mock_notion_client: MagicMock) -> None:
    """Test error handling when finding a page by URL."""
    mock_notion_client.databases.query = AsyncMock(side_effect=Exception("API Error"))
    api_service.client = mock_notion_client

    with pytest.raises(NotionAPIError) as exc_info:
        await api_service.query_database("test-db-id", {"URL": {"url": {"equals": "https://example.com"}}})
    assert "Failed to query database" in str(exc_info.value)
