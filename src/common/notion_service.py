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

    def find_page_by_url(self, url: str, url_property_name: str | None = None) -> dict[str, Any] | None:
        """Find a page in the database by URL.

        Args:
            url: The URL to search for.
            url_property_name: The name of the URL property in the database. If None, will auto-detect from schema.

        Returns:
            The page data if found, None otherwise.

        Raises:
            NotionAPIError: If there's an error querying the database.
        """
        try:
            # Auto-detect URL property name if not provided
            if url_property_name is None:
                database_schema = self.get_database_schema()
                url_property_name = self._find_url_property_name(database_schema)
                if url_property_name is None:
                    raise NotionAPIError(
                        "No URL property found in database schema. Cannot search for existing pages by URL."
                    )

            result = self.client.databases.query(
                database_id=self.database_id,
                filter={"property": url_property_name, "url": {"equals": url}},
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

    def save_or_update_extracted_data(
        self, url: str, extracted_data: dict[str, Any], url_property_name: str | None = None
    ) -> dict[str, Any]:
        """Save extracted data to Notion database, updating existing page if URL already exists.

        Args:
            url: The URL that was processed.
            extracted_data: The structured data extracted from the URL.
            url_property_name: The name of the URL property in the database. If None, will auto-detect from schema.

        Returns:
            The page data (either updated or newly created).

        Raises:
            NotionAPIError: If there's an error saving or updating the data.
        """
        try:
            # Get database schema to understand property types
            database_schema = self.get_database_schema()

            # Auto-detect URL property name if not provided
            if url_property_name is None:
                url_property_name = self._find_url_property_name(database_schema)
                if url_property_name is None:
                    raise NotionAPIError(
                        "No URL property found in database schema. Please ensure your Notion database has a URL property or specify the property name explicitly."
                    )

            # Check if page with this URL already exists
            existing_page = self.find_page_by_url(url, url_property_name)

            # Prepare properties for Notion API format
            properties = self._format_properties_for_notion(extracted_data, url, url_property_name, database_schema)

            if existing_page:
                # Update existing page
                page_id = existing_page["id"]
                return self.update_page_properties(page_id, properties)
            else:
                # Create new page
                return self.create_page(properties)

        except Exception as e:
            raise NotionAPIError(f"Failed to save or update data for URL {url}: {str(e)}") from e

    def _format_properties_for_notion(
        self, extracted_data: dict[str, Any], url: str, url_property_name: str, database_schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Format extracted data into Notion property format based on database schema.

        Args:
            extracted_data: The structured data extracted from the URL.
            url: The URL that was processed.
            url_property_name: The name of the URL property in the database.
            database_schema: The database schema from Notion to understand property types.

        Returns:
            Properties formatted for Notion API.
        """
        properties: dict[str, Any] = {}

        # Always include the URL
        properties[url_property_name] = {"url": url}

        # Format other extracted properties based on database schema and value type
        for key, value in extracted_data.items():
            if key == url_property_name:
                continue  # Skip if it's the URL property

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
                    properties[key] = {"number": float(value) if isinstance(value, (int, float, str)) else None}
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

    def _find_url_property_name(self, database_schema: dict[str, Any]) -> str | None:
        """Find the URL property name in the database schema.

        Args:
            database_schema: The database schema from Notion.

        Returns:
            The name of the URL property if found, None otherwise.
        """
        # First, look for properties with type 'url'
        for property_name, property_config in database_schema.items():
            if property_config.get("type") == "url":
                return property_name

        # If no URL type found, look for common URL property names
        common_url_names = [
            "URL",
            "url",
            "Job URL",
            "Job url",
            "Link",
            "Job Link",
            "Posting URL",
            "Application URL",
            "Source",
        ]

        for property_name in database_schema.keys():
            for common_name in common_url_names:
                if property_name.lower() == common_name.lower():
                    return property_name

        # If still not found, check for properties containing 'url' or 'link' in the name
        for property_name in database_schema.keys():
            property_name_lower = property_name.lower()
            if "url" in property_name_lower or "link" in property_name_lower or "website" in property_name_lower:
                return property_name

        return None
