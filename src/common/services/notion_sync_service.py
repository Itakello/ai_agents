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
    ) -> None:
        """Initialize the Notion sync service.

        Args:
            api_service: Optional Notion API service. If not provided, a new one is created.
            file_service: Optional Notion file service. If not provided, a new one is created.
            database_id: Optional Notion database ID. If not provided, uses the value from settings.
        """
        settings = get_settings()
        self.api_service = api_service or NotionAPIService()
        self.file_service = file_service or NotionFileService()
        self.database_id = database_id or settings.NOTION_DATABASE_ID

        # The service no longer performs automatic schema validation/patching –
        # call ``_ensure_required_properties`` explicitly via the *init* CLI
        # command when you need to create or repair the database schema.

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
            # Verify the schema – if missing properties we instruct the caller to run `init`.
            if not await self.is_database_verified():
                raise NotionAPIError("Database schema is missing required properties. Run the `init` command first.")

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
                # Inform the caller instead of auto-patching.
                raise NotionAPIError(
                    "Database schema is missing required properties. Run the `init` command first."
                ) from e

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
            # Ensure database is in the expected shape – no auto-fix here.
            if not await self.is_database_verified(database_id):
                raise NotionAPIError("Database schema is missing required properties. Run the `init` command first.")

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

                # ------------------------------------------------------
                # Add the *Job URL* manually – it is purposely excluded
                # from the LLM schema (#exclude directive) but **must** be
                # present in every page so we can look it up later.
                # ------------------------------------------------------
                formatted_payload["properties"][url_property] = {"url": url}

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
        # 2. Determine which updates are required
        # ------------------------------------------------------------------
        required_property_defs: dict[str, dict[str, Any]] = settings.REQUIRED_DATABASE_PROPERTIES

        # Payload that will be sent to Notion's *Update a database* endpoint.
        update_payload: dict[str, Any] = {}

        for req_name, req_cfg in required_property_defs.items():
            req_type: str = req_cfg["type"]  # e.g. "title", "url", …
            req_desc: str | None = req_cfg.get("description")

            existing_prop = database.properties.get(req_name)

            # --------------------------------------------------------------
            # Case 1 – Property with the *desired name* already exists.
            #          We just need to ensure its *type* and *description*
            #          match our requirements.
            # --------------------------------------------------------------
            if existing_prop is not None:
                needs_update = False
                prop_update: dict[str, Any] = {}

                # 1a. Type mismatch ⟹ try to convert the property type.
                if str(existing_prop.type) != req_type:
                    prop_update[req_type] = {}
                    needs_update = True

                # 1b. Description mismatch ⟹ update the description text.
                if req_desc is not None and existing_prop.description != req_desc:
                    prop_update["description"] = req_desc
                    needs_update = True

                if needs_update:
                    update_payload[req_name] = prop_update

                # Nothing further to do for this property.
                continue

            # --------------------------------------------------------------
            # Case 2 – Property is *missing* entirely.
            #          • For a *title* property we **rename** the existing
            #            title column (if any).
            #          • Otherwise we create a new property.
            # --------------------------------------------------------------
            if req_type == "title":
                # Look for any existing property whose *type* is "title".
                old_title_entry = next(
                    ((old_name, prop) for old_name, prop in database.properties.items() if prop.type == "title"),
                    None,
                )

                # If a column with the *desired name* already exists but is **not**
                # of type "title" we prefer **converting** that column instead of
                # renaming the existing title one – this avoids the (invalid)
                # scenario where we would end up with two properties sharing the
                # same name.
                desired_prop = database.properties.get(req_name)

                if desired_prop is not None and desired_prop.type != "title":
                    # Promote the existing column to be the title property.
                    convert_def: dict[str, Any] = {desired_prop.id: {"name": req_name}}
                    if req_desc is not None:
                        convert_def[desired_prop.id]["description"] = req_desc
                    update_payload.update(convert_def)
                    continue

                if old_title_entry is not None:
                    old_name, old_prop = old_title_entry
                    rename_def: dict[str, Any] = {"name": req_name}
                    # Notion disallows *description* on the primary title
                    # property – including it triggers a *"Cannot change
                    # title to a different property type"* validation error.
                    update_payload[old_prop.id] = rename_def
                    continue

            # 2b. Create a brand-new property with the required settings.
            new_prop_def: dict[str, Any] = {req_type: {}}
            if req_desc is not None:
                new_prop_def["description"] = req_desc
            update_payload[req_name] = new_prop_def

        # ------------------------------------------------------------------
        # 3. Apply updates (if any) and refresh local cache
        # ------------------------------------------------------------------
        if update_payload:
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

    async def is_database_verified(self, database_id: str | None = None) -> bool:
        """Return *True* if the database already contains all required properties.

        The check is purely *read-only* – it will *not* attempt to run any
        update operation against the Notion API.  The caller can use this to
        decide whether they need to run the ``init`` command (which *does*
        patch the schema) before executing higher-level actions such as
        *resume extract* or *resume tailor*.
        """

        db_id = database_id or self.database_id

        # Ensure we have a cached copy of the database definition.
        if self._cached_database is None or self._cached_database.id != db_id:
            self._cached_database = await self.get_database(db_id)

        database = self._cached_database
        required_property_defs: dict[str, dict[str, Any]] = get_settings().REQUIRED_DATABASE_PROPERTIES

        for req_name, req_cfg in required_property_defs.items():
            req_type: str = req_cfg["type"]
            req_desc: str | None = req_cfg.get("description")

            existing_prop = database.properties.get(req_name)
            if existing_prop is None:
                return False

            # Property exists – ensure its *type* and (if provided) description match.
            if str(existing_prop.type) != req_type:
                return False
            if req_desc is not None and existing_prop.description != req_desc:
                return False

        # All requirements satisfied.
        return True
