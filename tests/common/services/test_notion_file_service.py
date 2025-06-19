"""Tests for the NotionFileService class."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.exceptions.notion_exceptions import NotionFileError
from src.common.services import NotionFileService


@pytest.fixture
def mock_notion_client() -> MagicMock:
    """Create a mock Notion client."""
    client = MagicMock()
    client.request = AsyncMock()
    return client


@pytest.fixture
def file_service(mock_notion_client: MagicMock) -> NotionFileService:
    """Create a NotionFileService instance with a mock client."""
    return NotionFileService(api_key="test-api-key")


@pytest.fixture
def mock_file(tmp_path: Path) -> Path:
    """Create a temporary test file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Test content")
    return file_path


@pytest.mark.asyncio
async def test_create_file_upload_object(file_service: NotionFileService) -> None:
    """Test creating a file upload object."""

    def mock_post(*args: Any, **kwargs: Any) -> MagicMock:
        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={"id": "test-upload-id", "upload_url": "https://example.com/upload"})
        response.raise_for_status = MagicMock()
        return response

    with patch("requests.post", side_effect=mock_post) as mock_post_func:
        upload_id, upload_url = await file_service.create_file_upload_object("test.txt", "text/plain")
        assert upload_id == "test-upload-id"
        assert upload_url == "https://example.com/upload"
        mock_post_func.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_contents(file_service: NotionFileService, mock_file: Path) -> None:
    def mock_post(*args: Any, **kwargs: Any) -> MagicMock:
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        return response

    with patch("requests.post", side_effect=mock_post) as mock_post_func:
        await file_service.upload_file_contents("https://example.com/upload", mock_file, "text/plain")
        mock_post_func.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file(file_service: NotionFileService, mock_file: Path) -> None:
    def mock_post(*args: Any, **kwargs: Any) -> MagicMock:
        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={"id": "test-upload-id", "upload_url": "https://example.com/upload"})
        response.raise_for_status = MagicMock()
        return response

    def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
        """Mock the GET call that retrieves the existing page properties."""
        response = MagicMock()
        response.status_code = 200
        # Return a page object with an existing files list so we can verify that the service attempts to append.
        response.json = MagicMock(
            return_value={
                "properties": {
                    "test-property": {
                        "type": "files",
                        "files": [
                            {
                                "type": "file",
                                "file": {"url": "https://example.com/old.pdf", "expiry_time": "2025-01-01T00:00:00Z"},
                                "name": "old.pdf",
                            }
                        ],
                    }
                }
            }
        )
        response.raise_for_status = MagicMock()
        return response

    def mock_patch(*args: Any, **kwargs: Any) -> MagicMock:
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        return response

    with (
        patch("requests.post", side_effect=mock_post) as mock_post_func,
        patch.object(NotionFileService, "get_existing_files", return_value=[]) as mock_get_files,
        patch("requests.patch", side_effect=mock_patch) as mock_patch_func,
    ):
        await file_service.upload_file(
            mock_file,
            "test-page-id",
            "test-property",
        )
        mock_post_func.assert_called()
        mock_get_files.assert_called()
        mock_patch_func.assert_called()


@pytest.mark.asyncio
async def test_create_file_upload_object_error(file_service: NotionFileService) -> None:
    with patch("requests.post", side_effect=Exception("API Error")):
        with pytest.raises(NotionFileError) as exc_info:
            await file_service.create_file_upload_object("test.txt", "text/plain")
        assert "Failed to create file upload object" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_file_contents_error(file_service: NotionFileService, mock_file: Path) -> None:
    with patch("requests.post", side_effect=Exception("Upload Error")):
        with pytest.raises(NotionFileError) as exc_info:
            await file_service.upload_file_contents("https://example.com/upload", mock_file, "text/plain")
        assert "Failed to upload file contents" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_file_error(file_service: NotionFileService, mock_file: Path) -> None:
    with patch("requests.post", side_effect=Exception("API Error")):
        with pytest.raises(NotionFileError) as exc_info:
            await file_service.upload_file(
                mock_file,
                "test-page-id",
                "test-property",
            )
        assert "Failed to upload file" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_file_nonexistent_file(file_service: NotionFileService) -> None:
    nonexistent_file = Path("nonexistent.txt")
    with pytest.raises(NotionFileError) as exc_info:
        await file_service.upload_file(
            nonexistent_file,
            "test-page-id",
            "test-property",
        )
    assert "File does not exist" in str(exc_info.value)


# ---------------------------------------------------------------------------
# New tests: get_existing_files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_existing_files_success(file_service: NotionFileService) -> None:
    """Should return the existing list of files when the page contains them."""

    def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(
            return_value={
                "properties": {
                    "resume": {
                        "type": "files",
                        "files": [
                            {
                                "type": "file",
                                "file": {"url": "https://example.com/file.pdf", "expiry_time": "2025-01-01"},
                                "name": "file.pdf",
                            }
                        ],
                    }
                }
            }
        )
        response.raise_for_status = MagicMock()
        return response

    with patch("requests.get", side_effect=mock_get):
        files = await file_service.get_existing_files("page-id", "resume")
        assert isinstance(files, list)
        assert files and files[0]["name"] == "file.pdf"


@pytest.mark.asyncio
async def test_get_existing_files_error(file_service: NotionFileService) -> None:
    """Should return empty list when GET fails."""

    with patch("requests.get", side_effect=Exception("API Error")):
        files = await file_service.get_existing_files("page-id", "resume")
        assert files == []
