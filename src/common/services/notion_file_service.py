"""Notion file service for handling file operations."""

import mimetypes
from pathlib import Path

import requests

from src.common.exceptions.notion_exceptions import NotionFileError
from src.core.config import get_settings


class NotionFileService:
    """Service for handling file operations with Notion."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the Notion file service.

        Args:
            api_key: Optional Notion API key. If not provided, uses the value from settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.NOTION_API_KEY

    async def create_file_upload_object(self, file_name: str, mime_type: str) -> tuple[str, str]:
        """Create a file upload object in Notion.

        Args:
            file_name: The name of the file to upload.
            mime_type: The MIME type of the file to upload.

        Returns:
            Tuple of (upload_id, upload_url).

        Raises:
            NotionFileError: If there's an error creating the upload object.
        """
        try:
            # The Direct Upload flow expects a call to the /file_uploads endpoint.
            payload = {"filename": file_name, "content_type": mime_type}

            resp = requests.post(
                "https://api.notion.com/v1/file_uploads",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Notion-Version": "2022-06-28",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["id"], data["upload_url"]
        except Exception as e:
            raise NotionFileError(f"Failed to create file upload object: {str(e)}") from e

    async def upload_file_contents(self, upload_url: str, file_path: Path, mime_type: str) -> None:
        """Upload file contents to Notion.

        Args:
            upload_url: The URL to upload the file to.
            file_path: The path to the file to upload.
            mime_type: The MIME type of the file.

        Raises:
            NotionFileError: If there's an error uploading the file.
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, mime_type)}
                resp = requests.post(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Notion-Version": "2022-06-28",
                    },
                    files=files,
                )
                resp.raise_for_status()
        except Exception as e:
            raise NotionFileError(f"Failed to upload file contents: {str(e)}") from e

    async def upload_file(self, file_path: str | Path, page_id: str, property_name: str) -> None:
        """Upload a file to a Notion page property.

        Args:
            file_path: The path to the file to upload.
            page_id: The ID of the page to upload to.
            property_name: The name of the property to upload to.

        Raises:
            NotionFileError: If there's an error uploading the file.
        """
        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            raise NotionFileError(f"File does not exist: {file_path}")

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            upload_id, upload_url = await self.create_file_upload_object(file_path.name, mime_type)

            await self.upload_file_contents(upload_url, file_path, mime_type)

            # Retrieve current files for the property so we can append the newly uploaded file.
            existing_files = await self.get_existing_files(page_id, property_name)

            # Append the new file to existing ones (if any)
            updated_files = existing_files + [
                {
                    "type": "file_upload",
                    "file_upload": {"id": upload_id},
                    "name": file_path.name,
                }
            ]

            # Attach the combined file list back to the page property
            resp = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                json={
                    "properties": {
                        property_name: {
                            "type": "files",
                            "files": updated_files,
                        }
                    }
                },
            )
            resp.raise_for_status()
        except Exception as e:
            raise NotionFileError(f"Failed to upload file: {str(e)}") from e

    async def get_existing_files(self, page_id: str, property_name: str) -> list[dict]:
        """Retrieve the current list of files stored in the given page property.

        If the request fails or the property does not exist / contains no files, an empty list is returned.

        Args:
            page_id: The Notion page ID.
            property_name: The name of the property whose files we want to fetch.

        Returns:
            A list of file objects as returned by the Notion API (can be empty).
        """
        try:
            resp = requests.get(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Notion-Version": "2022-06-28",
                },
            )
            resp.raise_for_status()
            page_data = resp.json()

            prop_val = page_data.get("properties", {}).get(property_name, {})
            if isinstance(prop_val, dict):
                files = prop_val.get("files", [])
                if isinstance(files, list):
                    return files
            return []
        except Exception:
            # We deliberately swallow errors here to avoid data loss in callers that only want to append.
            return []

    async def download_file(self, file_url: str) -> bytes:
        """Download a file from Notion.

        Args:
            file_url: The URL of the file to download.

        Returns:
            The file contents as bytes.

        Raises:
            NotionFileError: If there's an error downloading the file.
        """
        try:
            resp = requests.get(file_url)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            raise NotionFileError(f"Failed to download file: {str(e)}") from e
