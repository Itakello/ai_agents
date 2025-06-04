"""
NotionService provides functionality to interact with the Notion API.

This module contains the NotionService class which handles communication with the Notion API,
including fetching page content and updating page properties.
"""

import mimetypes
from pathlib import Path
from typing import Any

import requests
from notion_client import Client as NotionClient

from src.core.config import get_settings


class NotionAPIError(Exception):
    """Custom exception for Notion API errors."""

    pass


class NotionService:
    """A service class for interacting with the Notion API.

    This class provides methods to fetch page content and update page properties
    in a Notion database.
    """

    def __init__(self, api_key: str, database_id: str) -> None:
        """Initialize the NotionService with API key and database ID.

        Args:
            api_key: The Notion API integration token.
            database_id: The ID of the Notion database to interact with.
        """
        self.client = NotionClient(auth=api_key)
        self.database_id = database_id

    def get_page_content(self, page_id: str) -> dict[str, Any]:
        """Fetch the content of a Notion page by its ID.

        Args:
            page_id: The ID of the Notion page to fetch.

        Returns:
            A dictionary containing the page content.

        Raises:
            APIErrorCode: If there's an error communicating with the Notion API.
        """
        try:
            result = self.client.pages.retrieve(page_id=page_id)
            if isinstance(result, dict):
                return result
            raise ValueError("Unexpected return type from Notion API")
        except Exception as e:
            # Wrap any exception in our custom exception
            raise NotionAPIError(f"Failed to fetch page {page_id}: {str(e)}") from e

    def get_database_schema(self) -> dict[str, Any]:
        """Fetch the schema (properties) of the configured Notion database.

        Returns:
            A dictionary containing the database properties schema.

        Raises:
            NotionAPIError: If there's an error fetching the database schema.
        """
        try:
            result = self.client.databases.retrieve(database_id=self.database_id)
            if isinstance(result, dict) and "properties" in result:
                properties = result["properties"]
                if isinstance(properties, dict):
                    return properties
            raise ValueError("Unexpected return type from Notion API or missing properties")
        except Exception as e:
            raise NotionAPIError(f"Failed to fetch database schema for {self.database_id}: {str(e)}") from e

    def update_page_property(self, page_id: str, property_name: str, property_value: Any) -> dict[str, Any]:
        """Update a specific property on a Notion page.

        Args:
            page_id: The ID of the Notion page to update.
            property_name: The name of the property to update.
            property_value: The new value for the property.

        Returns:
            A dictionary containing the updated page data.

        Raises:
            NotionAPIError: If there's an error updating the page property.
        """
        try:
            result = self.client.pages.update(page_id=page_id, properties={property_name: property_value})
            if isinstance(result, dict):
                return result
            raise ValueError("Unexpected return type from Notion API")
        except Exception as e:
            raise NotionAPIError(f"Failed to update property '{property_name}' on page {page_id}: {str(e)}") from e

    def update_page_properties(self, page_id: str, properties_update: dict[str, Any]) -> dict[str, Any]:
        """Update multiple properties on a Notion page.

        Args:
            page_id: The ID of the Notion page to update.
            properties_update: A dictionary containing property updates. Can be in format:
                - {"property_name": property_value, ...} or
                - {"properties": {"property_name": property_value, ...}}

        Returns:
            A dictionary containing the updated page data.

        Raises:
            NotionAPIError: If there's an error updating the page properties.
        """
        try:
            # Handle both formats: with and without "properties" wrapper
            if "properties" in properties_update:
                properties = properties_update["properties"]
            else:
                properties = properties_update

            result = self.client.pages.update(page_id=page_id, properties=properties)
            if isinstance(result, dict):
                return result
            raise ValueError("Unexpected return type from Notion API")
        except Exception as e:
            raise NotionAPIError(f"Failed to update properties on page {page_id}: {str(e)}") from e

    def find_page_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        """Find a page in the database by its job ID.

        Args:
            job_id: The job ID to search for.

        Returns:
            The page data if found, None otherwise.

        Raises:
            NotionAPIError: If there's an error querying the database.
        """
        try:
            result = self.client.databases.query(
                database_id=self.database_id,
                filter={"property": "ID", "rich_text": {"equals": job_id}},
            )
            if isinstance(result, dict) and "results" in result and result["results"]:
                first_result = result["results"][0]
                return first_result if isinstance(first_result, dict) else None
            return None
        except Exception as e:
            raise NotionAPIError(f"Failed to search for page with job ID {job_id}: {str(e)}") from e

    def find_page_by_url(self, url: str, url_property_name: str | None = None) -> dict[str, Any] | None:
        """
        Find a page in the database by its URL property.

        Args:
            url: The job URL to search for.
            url_property_name: The property name for the URL in the database. If None, auto-detects from schema.

        Returns:
            The page data if found, None otherwise.
        Raises:
            NotionAPIError: If there's an error querying the database.
        """
        try:
            url_property = url_property_name or get_settings().JOB_URL_PROPERTY_NAME
            if not url_property:
                raise NotionAPIError("Could not determine URL property name in Notion database schema.")
            result = self.client.databases.query(
                database_id=self.database_id,
                filter={"property": url_property, "url": {"equals": url}},
            )
            if isinstance(result, dict) and "results" in result and result["results"]:
                first_result = result["results"][0]
                return first_result if isinstance(first_result, dict) else None
            return None
        except Exception as e:
            raise NotionAPIError(f"Failed to search for page with URL {url}: {str(e)}") from e

    def create_page(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a new page in the database.

        Args:
            properties: The properties to set on the new page.

        Returns:
            The created page data.

        Raises:
            NotionAPIError: If there's an error creating the page.
        """
        try:
            result = self.client.pages.create(parent={"database_id": self.database_id}, properties=properties)
            if isinstance(result, dict):
                return result
            raise ValueError("Unexpected return type from Notion API")
        except Exception as e:
            raise NotionAPIError(f"Failed to create page: {str(e)}") from e

    def save_or_update_extracted_data(self, url: str, extracted_data: dict[str, Any]) -> dict[str, Any]:
        """
        Save extracted data to Notion database, updating existing page if URL already exists.
        Always stores markdown content as a rich_text property.

        Args:
            url: The URL that was processed.
            extracted_data: The structured data extracted from the URL. Should include markdown content.
            url_property_name: The name of the URL property in the database. If None, will auto-detect from schema.

        Returns:
            The page data (either updated or newly created).
        Raises:
            NotionAPIError: If there's an error saving or updating the data.
        """
        try:
            database_schema = self.get_database_schema()
            # Check if page with this URL already exists
            existing_page = self.find_page_by_url(url)
            # Prepare properties for Notion API format
            properties = self._format_properties_for_notion(extracted_data, url, database_schema)
            if existing_page:
                page_id = existing_page["id"]
                return self.update_page_properties(page_id, properties)
            else:
                return self.create_page(properties)
        except Exception as e:
            raise NotionAPIError(f"Failed to save or update data for URL {url}: {str(e)}") from e

    def _format_properties_for_notion(
        self, extracted_data: dict[str, Any], url: str, database_schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Format extracted data into Notion property format based on database schema.

        Args:
            extracted_data: The structured data extracted from the URL.
            url: The URL that was processed.
            database_schema: The database schema from Notion to understand property types.

        Returns:
            Properties formatted for Notion API.
        """
        properties: dict[str, Any] = {}

        # Format other extracted properties based on database schema and value type
        for key, value in extracted_data.items():
            # Get the property configuration from database schema
            property_config = database_schema.get(key, {})
            property_type = property_config.get("type", "rich_text")

            # Format based on Notion property type
            if property_type == "title":
                properties[key] = {"title": [{"text": {"content": str(value)}}]}
            elif property_type == "rich_text":
                properties[key] = {"rich_text": [{"text": {"content": str(value)}}]}
            elif property_type == "number":
                try:
                    properties[key] = {"number": float(value) if isinstance(value, int | float | str) else None}
                except (ValueError, TypeError):
                    properties[key] = {"number": None}
            elif property_type == "checkbox":
                properties[key] = {"checkbox": bool(value)}
            elif property_type == "select":
                # For select properties, use the value as the option name
                if value is not None and str(value).strip():
                    properties[key] = {"select": {"name": str(value)}}
                else:
                    properties[key] = {"select": None}
            elif property_type == "multi_select":
                if isinstance(value, list):
                    properties[key] = {"multi_select": [{"name": str(item)} for item in value if str(item).strip()]}
                else:
                    # Split string values by common delimiters
                    value_str = str(value)
                    items = [item.strip() for item in value_str.replace(",", ";").split(";") if item.strip()]
                    properties[key] = {"multi_select": [{"name": item} for item in items]}
            elif property_type == "url":
                properties[key] = {"url": str(value) if value else None}
            elif property_type == "email":
                properties[key] = {"email": str(value) if value else None}
            elif property_type == "phone_number":
                properties[key] = {"phone_number": str(value) if value else None}
            elif property_type == "date":
                # Handle date properties - value should be in ISO format
                if value:
                    properties[key] = {"date": {"start": str(value)}}
                else:
                    properties[key] = {"date": None}
            else:
                # Default to rich_text for unknown property types
                properties[key] = {"rich_text": [{"text": {"content": str(value)}}]}

        return properties

    def upload_file_to_page_property(
        self,
        file_path: str | Path,
        page_id: str,
        property_name: str,
    ) -> str | None:
        """
        Uploads a file to a Notion page property.

        Returns:
            str: The file path as a string if the property is of type 'url' or 'rich_text'.
            None: If the property is of type 'files' or on error.

        Args:
            file_path: Path to the file to upload.
            page_id: The ID of the Notion page to update.
            property_name: The name of the property to update (must be of type 'files').
        Raises:
            NotionAPIError: If the upload fails or property type is not 'files'.
        """

        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            raise NotionAPIError(f"File does not exist: {file_path}")

        schema = self.get_database_schema()
        prop_schema = schema.get(property_name, {})
        prop_type = prop_schema.get("type")

        if prop_type != "files":
            raise NotionAPIError(
                f"Property '{property_name}' is of type '{prop_type}'. "
                f"This function currently only supports 'files', 'url', or 'rich_text' for this operation."
            )

        # Step 1: Create a File Upload object using Notion SDK
        file_name = file_path.name
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"  # Default MIME type

        try:
            # The NotionClient's request method handles auth, base URL, and standard headers.
            # The 'type' in the body here is Notion's internal 'file' type, not the mime_type.
            upload_obj_response = self.client.request(
                path="file_uploads",
                method="POST",
                body={"name": file_name, "type": "file"},
            )
            # The SDK's request method should return a parsed response or raise an error.
            upload_id = upload_obj_response["id"]
            upload_url = upload_obj_response["upload_url"]
        except Exception as e:
            raise NotionAPIError(f"Failed to create Notion file upload object: {e}") from e

        # Step 2: Upload the file contents
        try:
            with open(file_path, "rb") as f:
                # For S3 pre-signed URL, POST the raw file data with the correct Content-Type.
                # Notion-specific headers (Authorization, Notion-Version) are not needed for S3.
                s3_headers = {"Content-Type": mime_type}
                file_data = f.read()
                upload_resp = requests.post(
                    upload_url,
                    headers=s3_headers,
                    data=file_data,  # Send raw bytes
                    timeout=60,
                )
                # This will raise an HTTPError if the S3 upload fails (e.g., 400, 403, 500).
                # The surrounding try-except block will catch this and re-raise as NotionAPIError.
                upload_resp.raise_for_status()
        except Exception as e:
            raise NotionAPIError(f"Failed to upload file contents to Notion: {e}") from e

        # Step 3: Attach the file to the page property
        try:
            files_value = [
                {
                    "type": "file_upload",
                    "file_upload": {"id": upload_id},
                    "name": file_name,
                }
            ]
            self.update_page_property(page_id, property_name, {"files": files_value})
        except Exception as e:
            raise NotionAPIError(f"Failed to attach uploaded file to Notion page: {e}") from e

        return None

    def get_file_from_page_property(self, page_id: str, property_name: str) -> str | None:
        """
        Retrieve markdown content from a Notion 'files' property on the given page.

        Args:
            page_id: The ID of the Notion page.
            property_name: The name of the property to retrieve (must be of type 'files').

        Returns:
            The markdown content as a string, or None if not found or download fails.
        """

        try:
            page = self.get_page_content(page_id)
            prop = page.get("properties", {}).get(property_name)
            if not prop or prop.get("type") != "files":
                return None
            files = prop.get("files", [])
            if not files or not isinstance(files, list):
                return None
            file_url = files[0].get("file", {}).get("url") or files[0].get("external", {}).get("url")
            if not file_url:
                return None
            resp = requests.get(file_url)
            if resp.ok:
                return resp.text
            return None
        except Exception:
            return None
