"""
NotionService provides functionality to interact with the Notion API.

This module contains the NotionService class which handles communication with the Notion API,
including fetching page content and updating page properties.
"""

from typing import Any

from notion_client import Client as NotionClient


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
