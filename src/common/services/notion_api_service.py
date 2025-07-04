"""Notion API service for handling raw API communication."""

import asyncio
from typing import Any

from notion_client import AsyncClient as NotionClient

from src.common.exceptions.notion_exceptions import NotionAPIError
from src.common.models.notion_database import NotionDatabase
from src.common.models.notion_page import NotionPage
from src.core.config import get_settings


class NotionAPIService:
    """Service for handling raw API communication with Notion."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the Notion API service.

        Args:
            api_key: Optional Notion API key. If not provided, uses the value from settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.NOTION_API_KEY
        self.client = NotionClient(auth=self.api_key)

    async def get_page(self, page_id: str) -> NotionPage:
        """Get a page by ID.

        Args:
            page_id: The ID of the page to get.

        Returns:
            The page data.

        Raises:
            NotionAPIError: If there's an error getting the page.
        """
        try:
            result = await self.client.pages.retrieve(page_id=page_id)
            return NotionPage.model_validate(result)
        except Exception as e:
            raise NotionAPIError(f"Failed to get page {page_id}: {str(e)}") from e

    async def get_database(self, database_id: str) -> NotionDatabase:
        """Get a database by ID.

        Args:
            database_id: The ID of the database to get.

        Returns:
            The database data.

        Raises:
            NotionAPIError: If there's an error getting the database.
        """
        try:
            result = await self.client.databases.retrieve(database_id=database_id)
            return NotionDatabase.model_validate(result)
        except Exception as e:
            raise NotionAPIError(f"Failed to get database {database_id}: {str(e)}") from e

    async def update_page(self, page_id: str, properties: dict[str, Any]) -> NotionPage:
        """Update a page's properties.

        Args:
            page_id: The ID of the page to update.
            properties: The properties to update.

        Returns:
            The updated page data.

        Raises:
            NotionAPIError: If there's an error updating the page.
        """
        try:
            result = await self.client.pages.update(page_id=page_id, properties=properties)
            return NotionPage.model_validate(result)
        except Exception as e:
            raise NotionAPIError(f"Failed to update page {page_id}: {str(e)}") from e

    async def update_database(self, database_id: str, properties: dict[str, Any]) -> NotionDatabase:
        """Update a database's properties with basic retry / back-off handling.

        The Notion API occasionally returns a *409 Conflict* or the misleading
        *"Cannot change title to a different property type"* validation error
        while merely renaming the title column.  Both conditions are
        transient – retrying after a short delay almost always succeeds.

        This helper retries up to **3** times with exponential back-off for
        those *specific* cases before surfacing the error to the caller.
        """

        max_attempts = 3
        backoff_seconds = 0.8

        for attempt in range(1, max_attempts + 1):
            try:
                result = await self.client.databases.update(database_id=database_id, properties=properties)
                return NotionDatabase.model_validate(result)
            except Exception as e:  # noqa: BLE001 – we inspect the message
                # Convert to plain string once for re-use.
                msg = str(e)

                # -----------------------------------------------------------------
                # Retry conditions
                # -----------------------------------------------------------------
                should_retry = (
                    "Conflict occurred while saving" in msg or "Cannot change title to a different property type" in msg
                )

                if should_retry and attempt < max_attempts:
                    await asyncio.sleep(backoff_seconds * (2 ** (attempt - 1)))
                    continue

                # No more retries or non-retryable error – raise
                raise NotionAPIError(f"Failed to update database {database_id}: {msg}") from e

        # Should never reach here – added to satisfy type checkers.
        raise NotionAPIError(f"Failed to update database {database_id}: unknown error")

    async def create_page(self, parent: dict[str, Any], properties: dict[str, Any]) -> NotionPage:
        """Create a new page.

        Args:
            parent: The parent object (database or page).
            properties: The properties for the new page.

        Returns:
            The created page data.

        Raises:
            NotionAPIError: If there's an error creating the page.
        """
        try:
            result = await self.client.pages.create(parent=parent, properties=properties)
            return NotionPage.model_validate(result)
        except Exception as e:
            raise NotionAPIError(f"Failed to create page: {str(e)}") from e

    async def query_database(self, database_id: str, filter: dict[str, Any] | None = None) -> list[NotionPage]:
        """Query a database.

        Args:
            database_id: The ID of the database to query.
            filter: Optional filter to apply to the query.

        Returns:
            The query results.

        Raises:
            NotionAPIError: If there's an error querying the database.
        """
        try:
            result = await self.client.databases.query(database_id=database_id, filter=filter)
            return [NotionPage.model_validate(page) for page in result.get("results", [])]
        except Exception as e:
            raise NotionAPIError(f"Failed to query database {database_id}: {str(e)}") from e
