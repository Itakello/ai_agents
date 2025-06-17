"""
NotionService provides functionality to interact with the Notion API.

This module contains the NotionService class which handles communication with the Notion API,
including fetching page content and updating page properties.
"""

import mimetypes
from pathlib import Path
from typing import Any

import requests
from loguru import logger
from notion_client import Client as NotionClient

from src.common.models import (
    NotionDatabase,
    NotionDatabaseSchemaProperty,
    NotionPage,
)
from src.core.config import get_settings


class NotionAPIError(Exception):
    """Custom exception for Notion API errors."""

    pass


class NotionService:
    """Service for interacting with the Notion API."""

    def __init__(self, api_key: str | None = None, database_id: str | None = None, client: Any | None = None) -> None:
        """Initialize the NotionService.

        Args:
            api_key: Optional Notion API key. If not provided, uses the value from settings.
            database_id: Optional Notion database ID. If not provided, uses the value from settings.
            client: Optional Notion client. If not provided, a new client is created using the API key.
        """
        settings = get_settings()
        self.api_key = api_key or settings.NOTION_API_KEY
        self.database_id = database_id or settings.NOTION_DATABASE_ID
        self.client = client or NotionClient(auth=self.api_key)
        self._verify_database_schema()

    def _verify_database_schema(self) -> None:
        """Verify that the database has all required properties with correct types."""
        schema = self.get_database_schema()
        missing_props, type_mismatches = self._check_schema(schema)

        if missing_props or type_mismatches:
            logger.warning(
                "Database schema issues found: missing=%s, type_mismatches=%s",
                missing_props,
                type_mismatches,
            )
            self._fix_schema(schema, missing_props, type_mismatches)

    def _check_schema(self, schema: dict[str, Any]) -> tuple[list[str], list[tuple[str, str, str]]]:
        """Check if the database schema matches required properties.

        Args:
            schema: Current database schema from Notion API

        Returns:
            Tuple of (missing_properties, type_mismatches)
        """
        missing_props = []
        type_mismatches = []
        settings = get_settings()

        for prop_name, prop_config in settings.REQUIRED_DATABASE_PROPERTIES.items():
            if prop_name not in schema:
                missing_props.append(prop_name)
                continue

            current_type = schema[prop_name]["type"]
            required_type = prop_config["type"]
            if current_type != required_type:
                type_mismatches.append((prop_name, current_type, required_type))

        return missing_props, type_mismatches

    def _fix_schema(
        self,
        schema: dict[str, Any],
        missing_props: list[str],
        type_mismatches: list[tuple[str, str, str]],
    ) -> None:
        """Fix database schema issues by adding missing properties and updating types.

        Args:
            schema: Current database schema
            missing_props: List of missing property names
            type_mismatches: List of (property_name, current_type, required_type) tuples
        """
        settings = get_settings()
        # Add missing properties
        for prop_name in missing_props:
            prop_config = settings.REQUIRED_DATABASE_PROPERTIES[prop_name]
            self.update_schema(
                {
                    "properties": {
                        prop_name: {
                            "type": prop_config["type"],
                            "name": prop_name,
                            "description": prop_config.get("description", ""),
                        }
                    }
                }
            )
            logger.info("Added missing property: %s (%s)", prop_name, prop_config["type"])

        # Update property types
        for prop_name, current_type, required_type in type_mismatches:
            prop_config = settings.REQUIRED_DATABASE_PROPERTIES[prop_name]
            self.update_schema(
                {
                    "properties": {
                        prop_name: {
                            "type": required_type,
                            "name": prop_name,
                            "description": prop_config.get("description", ""),
                        }
                    }
                }
            )
            logger.info(
                "Updated property type: %s (%s -> %s)",
                prop_name,
                current_type,
                required_type,
            )

    def update_schema(self, schema_update: dict[str, Any]) -> None:
        """Update the database schema.

        Args:
            schema_update: Schema update to apply
        """
        try:
            self.client.databases.update(
                database_id=self.database_id,
                properties=schema_update["properties"],
            )
        except Exception as e:
            logger.error("Failed to update database schema: %s", str(e))
            raise

    def get_page(self, page_id: str) -> NotionPage:
        """Fetch the content of a Notion page by its ID.

        Args:
            page_id: The ID of the Notion page to fetch.

        Returns:
            A NotionPage instance containing the page content.

        Raises:
            NotionAPIError: If there's an error communicating with the Notion API.
        """
        try:
            raw_result = self.client.pages.retrieve(page_id=page_id)
            return NotionPage.model_validate(raw_result)
        except Exception as e:
            raise NotionAPIError(f"Failed to fetch page {page_id}: {str(e)}") from e

    def get_database_schema(self) -> dict[str, Any]:
        """Fetch the schema (properties) of the configured Notion database.

        Returns:
            A dictionary containing the database properties schema.

        Raises:
            NotionAPIError: If there's an error fetching the database schema.
        """
        try:
            raw_result = self.client.databases.retrieve(database_id=self.database_id)
            # Add required fields for validation
            if isinstance(raw_result, dict):
                raw_result.update(
                    {
                        "created_time": raw_result.get("created_time", "2024-01-01T00:00:00.000Z"),
                        "last_edited_time": raw_result.get("last_edited_time", "2024-01-01T00:00:00.000Z"),
                        "title": raw_result.get("title", [{"plain_text": "Database"}]),
                    }
                )
                # Add name field to properties if missing
                for prop_name, prop in raw_result.get("properties", {}).items():
                    if isinstance(prop, dict) and "name" not in prop:
                        prop["name"] = prop_name

            db_model: NotionDatabase = NotionDatabase.model_validate(raw_result)

            return {
                name: prop.model_dump(mode="python") if isinstance(prop, NotionDatabaseSchemaProperty) else prop
                for name, prop in db_model.properties.items()
            }
        except Exception as e:
            raise NotionAPIError(f"Failed to fetch database schema for {self.database_id}: {str(e)}") from e

    def update_page_property(self, page_id: str, property_name: str, property_value: Any) -> NotionPage:
        """Update a specific property on a Notion page.

        Args:
            page_id: The ID of the Notion page to update.
            property_name: The name of the property to update.
            property_value: The new value for the property.

        Returns:
            A NotionPage instance containing the updated page data.

        Raises:
            NotionAPIError: If there's an error updating the page property.
        """
        try:
            raw_result = self.client.pages.update(page_id=page_id, properties={property_name: property_value})
            return NotionPage.model_validate(raw_result)
        except Exception as e:
            raise NotionAPIError(f"Failed to update property '{property_name}' on page {page_id}: {str(e)}") from e

    def update_page_properties(self, page_id: str, properties_update: dict[str, Any]) -> NotionPage:
        """Update multiple properties on a Notion page.

        Args:
            page_id: The ID of the Notion page to update.
            properties_update: A dictionary containing property updates. Can be in format:
                - {"property_name": property_value, ...} or
                - {"properties": {"property_name": property_value, ...}}

        Returns:
            A NotionPage instance containing the updated page data.

        Raises:
            NotionAPIError: If there's an error updating the page properties.
        """
        # Unwrap 'properties' key if present
        if "properties" in properties_update and isinstance(properties_update["properties"], dict):
            properties = properties_update["properties"]
        else:
            properties = properties_update
        try:
            raw_result = self.client.pages.update(page_id=page_id, properties=properties)
            return NotionPage.model_validate(raw_result)
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
            properties = self._format_properties_for_notion(extracted_data, database_schema)
            if existing_page:
                page_id = existing_page["id"]
                return self.update_page_properties(page_id, properties).model_dump(mode="python")
            else:
                prop_name = get_settings().JOB_URL_PROPERTY_NAME
                properties[prop_name] = {"url": url}
                return self.create_page(properties)
        except Exception as e:
            raise NotionAPIError(f"Failed to save or update data for URL {url}: {str(e)}") from e

    def _format_properties_for_notion(
        self, extracted_data: dict[str, Any], database_schema: dict[str, Any]
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
    ) -> None:
        """
        Upload a file to a Notion page property of type 'files'.

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
                f"Property '{property_name}' is of type '{prop_type}'. This function only supports 'files' properties."
            )
        file_name = file_path.name
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        try:
            upload_id, upload_url = self._create_file_upload_object(file_name)
            self._upload_file_contents(upload_url, file_path, mime_type)
            self.append_file_to_page_property(page_id, property_name, upload_id, file_name)
        except Exception as e:
            raise NotionAPIError(f"File upload failed: {e}") from e

    def _create_file_upload_object(self, file_name: str) -> tuple[str, str]:
        """
        Create a file upload object in Notion and return (upload_id, upload_url).
        """
        try:
            resp = self.client.request(
                path="file_uploads",
                method="POST",
                body={"name": file_name, "type": "file"},
            )
            return resp["id"], resp["upload_url"]
        except Exception as e:
            raise NotionAPIError(f"Failed to create Notion file upload object: {e}") from e

    def _upload_file_contents(self, upload_url: str, file_path: Path, mime_type: str) -> None:
        """
        Upload the file contents to the provided upload_url (Notion expects multipart/form-data).
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, mime_type)}
                resp = requests.post(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {get_settings().NOTION_API_KEY}",
                        "Notion-Version": "2022-06-28",
                    },
                    files=files,
                )
                resp.raise_for_status()
        except Exception as e:
            raise NotionAPIError(f"Failed to upload file contents: {e}") from e

    def append_file_to_page_property(self, page_id: str, property_name: str, upload_id: str, file_name: str) -> None:
        """
        Append an uploaded file to the Notion page property without removing existing files.

        Args:
            page_id: The ID of the Notion page to update.
            property_name: The name of the property to update (must be of type 'files').
            upload_id: The Notion upload ID for the new file.
            file_name: The name of the file to display in Notion.

        Raises:
            NotionAPIError: If the file cannot be appended.
        """
        try:
            # Fetch the current files property
            page = self.get_page(page_id)
            prop = page.properties.get(property_name)
            existing_files: list[dict[str, Any]] = []
            if prop and prop.type == "files" and prop.files:
                existing_files = [f.model_dump(mode="python") for f in prop.files]
            # Append the new file
            new_file = {
                "type": "file_upload",
                "file_upload": {"id": upload_id},
                "name": file_name,
            }
            files_value = existing_files + [new_file]
            self.update_page_property(page_id, property_name, {"files": files_value})
        except Exception as e:
            raise NotionAPIError(f"Failed to append uploaded file to Notion page: {e}") from e

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
            page = self.get_page(page_id)
            prop = page.properties.get(property_name)
            if not prop or prop.type != "files" or not prop.files:
                return None
            file_obj = prop.files[0]
            file_url = file_obj.url
            if not file_url:
                return None
            resp = requests.get(file_url)
            if resp.ok:
                return resp.text
            return None
        except Exception:
            return None
