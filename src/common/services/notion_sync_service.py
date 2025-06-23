"""Notion sync service for coordinating API and file operations."""

import asyncio
from typing import Any

from src.common.exceptions.notion_exceptions import NotionAPIError, NotionFileError
from src.common.models.notion_database import NotionDatabase
from src.common.models.notion_page import NotionPage
from src.common.services.notion_api_service import NotionAPIService
from src.common.services.notion_file_service import NotionFileService
from src.core.config import get_settings


class NotionSyncService:
    """Service for coordinating Notion API and file operations."""

    def __init__(
        self,
        api_service: NotionAPIService | None = None,
        file_service: NotionFileService | None = None,
        database_id: str | None = None,
        *,
        auto_ensure_schema: bool = True,
    ) -> None:
        """Initialize the Notion sync service.

        Args:
            api_service: Optional Notion API service. If not provided, a new one is created.
            file_service: Optional Notion file service. If not provided, a new one is created.
            database_id: Optional Notion database ID. If not provided, uses the value from settings.
            auto_ensure_schema: When ``True`` (default) the service verifies and
                patches the database schema immediately.  Disable for special
                scenarios (e.g. offline tests) where no API calls should be made.
        """
        settings = get_settings()
        self.api_service = api_service or NotionAPIService()
        self.file_service = file_service or NotionFileService()
        self.database_id = database_id or settings.NOTION_DATABASE_ID

        # Ensure database schema once during initialisation.  If we're already
        # inside an active event-loop (e.g. when the caller uses
        # ``asyncio.run`` higher up), we *schedule* the async task instead of
        # calling ``asyncio.run`` which would raise *"cannot be called from a
        # running event loop"*.

        if auto_ensure_schema:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is None:
                # Safe to run a temporary loop.
                self._ensure_required_properties_sync()
            else:
                # Fire-and-forget – caller can await ``_ensure_required_properties``
                # themselves if they need to ensure completion.
                running_loop.create_task(self._ensure_required_properties())

    _cached_database: NotionDatabase | None = None  # class-level cache per instance

    async def get_database(self, database_id: str) -> NotionDatabase:
        """Get a Notion database.

        Args:
            database_id: The ID of the database to get.

        Returns:
            The Notion database.

        Raises:
            NotionAPIError: If there's an error getting the database.
        """
        try:
            raw_result = await self.api_service.get_database(database_id)
            return NotionDatabase.model_validate(raw_result)
        except Exception as e:
            raise NotionAPIError(f"Failed to get database: {str(e)}") from e

    async def get_page(self, page_id: str) -> NotionPage:
        """Get a Notion page.

        Args:
            page_id: The ID of the page to get.

        Returns:
            The Notion page.

        Raises:
            NotionAPIError: If there's an error getting the page.
        """
        try:
            raw_result = await self.api_service.get_page(page_id)
            return NotionPage.model_validate(raw_result)
        except Exception as e:
            raise NotionAPIError(f"Failed to get page: {str(e)}") from e

    async def update_page(self, page_id: str, properties: dict[str, Any]) -> NotionPage:
        """Update a Notion page.

        Args:
            page_id: The ID of the page to update.
            properties: The properties to update.

        Returns:
            The updated Notion page.

        Raises:
            NotionAPIError: If there's an error updating the page.
        """
        try:
            raw_result = await self.api_service.update_page(page_id, properties)
            return NotionPage.model_validate(raw_result)
        except Exception as e:
            raise NotionAPIError(f"Failed to update page: {str(e)}") from e

    async def create_page(self, database_id: str, properties: dict[str, Any]) -> NotionPage:
        """Create a new Notion page.

        Args:
            database_id: The ID of the database to create the page in.
            properties: The properties for the new page.

        Returns:
            The created Notion page.

        Raises:
            NotionAPIError: If there's an error creating the page.
        """
        try:
            return await self.api_service.create_page({"database_id": database_id}, properties)
        except Exception as e:
            raise NotionAPIError(f"Failed to create page: {str(e)}") from e

    async def upload_file_to_page(self, file_path: str, page_id: str, property_name: str) -> NotionPage:
        """Upload a file to a Notion page property.

        Args:
            file_path: The path to the file to upload.
            page_id: The ID of the page to upload to.
            property_name: The name of the property to upload to.

        Returns:
            The updated Notion page.

        Raises:
            NotionAPIError: If there's an error uploading the file.
            NotionFileError: If there's an error with the file operation.
        """
        try:
            # Delegate the heavy lifting to the file service.
            await self.file_service.upload_file(file_path, page_id, property_name)

            # Return the refreshed page to the caller so they get the latest state.
            return await self.get_page(page_id)
        except Exception as e:
            if isinstance(e, NotionFileError):
                raise
            raise NotionAPIError(f"Failed to upload file to page: {str(e)}") from e

    async def find_page_by_url(
        self, url: str, url_property_name: str | None = None
    ) -> NotionPage | dict[str, Any] | None:
        """Find a page in the database by its URL.

        Args:
            url: The URL to search for.
            url_property_name: Optional name of the URL property. If not provided, uses the value from settings.

        Returns:
            The found page, or None if not found.

        Raises:
            NotionAPIError: If there's an error searching for the page.
        """
        try:
            # Ensure the database contains the URL property before querying.
            await self._ensure_required_properties()

            settings = get_settings()
            url_property = url_property_name or settings.JOB_URL_PROPERTY_NAME
            if not url_property:
                raise NotionAPIError("Could not determine URL property name")

            result = await self.api_service.query_database(
                self.database_id,
                filter={"property": url_property, "url": {"equals": url}},
            )

            if result:
                return result[0]
            return None
        except Exception as e:
            raise NotionAPIError(f"Failed to find page by URL: {str(e)}") from e

    async def query_database(self, database_id: str, filter: dict[str, Any] | None = None) -> list[NotionPage]:
        """Query a Notion database.

        Args:
            database_id: The ID of the database to query.
            filter: Optional filter to apply to the query.

        Returns:
            The query results.

        Raises:
            NotionAPIError: If there's an error querying the database.
        """
        try:
            return await self.api_service.query_database(database_id, filter)
        except Exception as e:
            # Detect the specific "missing property" error coming from Notion and
            # attempt to automatically patch the database schema once before
            # re-trying the query.
            error_msg = str(e)
            if "Could not find property" in error_msg:
                # Best-effort schema fix – if this still fails we'll bubble up
                # the original error for the caller to handle.
                await self._ensure_required_properties(database_id)
                return await self.api_service.query_database(database_id, filter)

            raise NotionAPIError(f"Failed to query database: {error_msg}") from e

    async def save_or_update_extracted_data(
        self, database_id: str, url: str, extracted_data: dict[str, Any]
    ) -> NotionPage:
        """Save or update extracted data in a Notion page.

        Args:
            database_id: The ID of the database to save to.
            url: The URL of the page to save or update.
            extracted_data: The data to save.

        Returns:
            The saved or updated Notion page.

        Raises:
            NotionAPIError: If there's an error saving or updating the data.
        """
        try:
            # Make sure all required properties (particularly the URL one) are
            # present in the database before we attempt any operations that
            # rely on them.
            await self._ensure_required_properties(database_id)

            # Find existing page by URL
            url_property = get_settings().JOB_URL_PROPERTY_NAME

            pages = await self.query_database(
                database_id,
                filter={"property": url_property, "url": {"equals": url}},
            )
            if pages:
                # Update existing page
                page = pages[0]

                # Convert ``extracted_data`` (simple scalar / list values) into
                # the nested structure expected by the Notion API for each
                # property *based on the existing page schema*.
                notion_properties = page.format_properties_for_notion(extracted_data)

                return await self.update_page(page.id, notion_properties)
            else:
                # ----------------------------------------------------------
                # Create a **new** page – convert the plain LLM output into
                # the nested JSON structure required by the Notion API first.
                # ----------------------------------------------------------

                # Local import to avoid circular dependency during module
                # initialisation (metadata_extraction→extractor_service→
                # NotionSyncService).
                from src.metadata_extraction.schema_utils import (
                    build_notion_properties_from_llm_output,
                )

                db_schema = self.get_database_schema(database_id)
                formatted_payload = build_notion_properties_from_llm_output(
                    extracted_data,
                    db_schema,
                )

                return await self.create_page(database_id, formatted_payload["properties"])
        except Exception as e:
            raise NotionAPIError(f"Failed to save or update extracted data: {str(e)}") from e

    def get_database_schema(self, database_id: str | None = None, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return the database *properties* as a plain dict.

        The schema is fetched once and cached in the instance.  Subsequent
        calls return the cached representation unless *force_refresh* is
        True.
        """

        if self._cached_database is not None and not force_refresh:
            return {name: prop.model_dump(exclude_none=True) for name, prop in self._cached_database.properties.items()}

        async def _inner(db_id: str) -> NotionDatabase:
            return await self.get_database(db_id)

        db_id = database_id or self.database_id

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is None:
            # No active loop – safe to use asyncio.run
            self._cached_database = asyncio.run(_inner(db_id))
        else:
            # Spawn a *temporary* loop so we don't interfere with the current
            # one.  This mirrors the behaviour of ``asyncio.run`` but avoids
            # the RuntimeError.
            tmp_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(tmp_loop)
                self._cached_database = tmp_loop.run_until_complete(_inner(db_id))
            finally:
                tmp_loop.close()
                asyncio.set_event_loop(running_loop)

        # NOTE: ``asyncio.run`` creates a *temporary* event-loop which is
        # automatically closed once the coroutine completes.  The
        # ``NotionClient`` instance kept inside ``self.api_service`` is bound
        # to that loop – any subsequent awaits using the same client will
        # therefore crash with *"Event loop is closed"*.  Re-creating the
        # ``NotionAPIService`` (and thus its internal ``NotionClient``)
        # attaches it to whatever loop is active **next** time we run an
        # async call.

        self.api_service = NotionAPIService()

        return {name: prop.model_dump(exclude_none=True) for name, prop in self._cached_database.properties.items()}

    async def _ensure_required_properties(self, database_id: str | None = None) -> None:
        """Ensure that the database contains all required properties.

        This helper fetches the current database schema and compares it
        against the *REQUIRED_DATABASE_PROPERTIES* declared in the global
        ``Settings`` instance.  Any missing properties are created via the
        Notion *Update a database* endpoint so that subsequent queries or
        page creations that rely on those fields succeed.
        """

        db_id = database_id or self.database_id
        settings = get_settings()

        # ------------------------------------------------------------------
        # 1. Retrieve (and cache) the database definition
        # ------------------------------------------------------------------
        if self._cached_database is None or self._cached_database.id != db_id:
            self._cached_database = await self.get_database(db_id)

        database = self._cached_database

        # ------------------------------------------------------------------
        # 2. Work out which required properties are missing
        # ------------------------------------------------------------------
        required_property_defs: dict[str, dict[str, Any]] = settings.REQUIRED_DATABASE_PROPERTIES
        required_property_types = {name: cfg["type"] for name, cfg in required_property_defs.items()}

        missing = database.verify_schema(required_property_types)

        # Special-case: if the *Title* property is considered missing but
        # another property of type "title" already exists, we'll **rename** it
        # instead of creating a second title column (which Notion forbids).

        if "Title" in missing:
            # Find the first property whose type is "title"
            for old_name, prop in database.properties.items():
                if prop.type == "title":
                    # Build rename payload – keep the same type but change the
                    # display name to "Title".
                    rename_payload: dict[str, Any] = {old_name: {"name": "Title"}}
                    # Preserve / set description if provided in config.
                    title_desc = required_property_defs.get("Title", {}).get("description")
                    if title_desc:
                        rename_payload[old_name]["description"] = title_desc
                    try:
                        self._cached_database = await self.api_service.update_database(db_id, rename_payload)
                    except Exception:  # pragma: no cover
                        raise

                    # Refresh local reference and recompute missing set
                    database = self._cached_database
                    missing = database.verify_schema(required_property_types)
                    break

        # After the rename attempt, remove any properties now satisfied.
        if not missing:
            return

        # ------------------------------------------------------------------
        # 3. Build payload for any *remaining* missing properties
        # ------------------------------------------------------------------
        update_payload: dict[str, Any] = {}
        for prop_name in missing:
            # Skip title property if we've already renamed it
            if prop_name == "Title":
                continue
            prop_type = required_property_types[prop_name]
            prop_desc = required_property_defs[prop_name].get("description")

            new_prop_obj: dict[str, Any] = {prop_type: {}}
            if prop_desc:
                new_prop_obj["description"] = prop_desc

            update_payload[prop_name] = new_prop_obj

        if update_payload:
            # ------------------------------------------------------------------
            # 4. Send update request and refresh cache
            # ------------------------------------------------------------------
            try:
                self._cached_database = await self.api_service.update_database(db_id, update_payload)
            except Exception:  # pragma: no cover
                raise

    def _ensure_required_properties_sync(self) -> None:
        """Ensure that the database contains all required properties.

        This helper fetches the current database schema and compares it
        against the *REQUIRED_DATABASE_PROPERTIES* declared in the global
        ``Settings`` instance.  Any missing properties are created via the
        Notion *Update a database* endpoint so that subsequent queries or
        page creations that rely on those fields succeed.
        """

        async def _inner() -> None:
            await self._ensure_required_properties()

        asyncio.run(_inner())
