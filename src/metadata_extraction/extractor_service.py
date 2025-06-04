"""
ExtractorService provides core logic for extracting metadata from job descriptions.

This module contains the ExtractorService class which orchestrates the extraction of
structured metadata from job descriptions using OpenAI's language models and
Notion database schemas.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from crawl4ai import AsyncWebCrawler  # type: ignore
from crawl4ai.async_configs import BrowserConfig, CacheMode, CrawlerRunConfig  # type: ignore
from crawl4ai.models import CrawlResultContainer  # type: ignore

from ..common.llm_clients import OpenAIClient
from ..common.notion_service import NotionService
from ..common.utils import read_file_content, replace_prompt_placeholders
from ..core.config import get_settings
from .schema_utils import create_openai_schema_from_notion_database


class ExtractorServiceError(Exception):
    """Custom exception for ExtractorService errors."""

    pass


class ExtractorService:
    """A service class for extracting metadata from job descriptions.

    This class combines OpenAI's language models with Notion database schemas to
    extract structured metadata from unstructured job description text.
    """

    def __init__(
        self, openai_client: OpenAIClient, notion_service: NotionService, add_properties_options: bool = True
    ) -> None:
        """Initialize the ExtractorService with required clients.

        Args:
            openai_client: An initialized OpenAI client for LLM interactions.
            notion_service: An initialized Notion service for database operations.
            add_properties_options: Whether to add options to select/multi_select properties.
        """
        self.openai_client = openai_client
        self.notion_service = notion_service
        self.add_properties_options = add_properties_options

    def extract_metadata_from_job_url(
        self,
        job_url: str,
        notion_database_schema: dict[str, Any],
        model_name: str,
    ) -> dict[str, Any]:
        """Extract structured metadata from a job posting URL using crawl4ai + OpenAI.

        Args:
            job_url: The URL of the job posting to analyze.
            notion_database_schema: The Notion database properties schema for structuring the output.
            model_name: The name of the OpenAI model to use.

        Returns:
            A dictionary containing the extracted metadata in a format compatible with OpenAI's
            structured output, ready for conversion to Notion format.

        Raises:
            ExtractorServiceError: If there's an error during the   process.
        """
        if not job_url.strip():
            raise ExtractorServiceError("Job URL cannot be empty")

        if not notion_database_schema:
            raise ExtractorServiceError("Notion database schema cannot be empty")

        try:
            extracted_metadata = self._extract_metadata_with_crawl4ai(job_url, notion_database_schema, model_name)
        except Exception as e:
            if isinstance(e, ExtractorServiceError):
                raise
            raise ExtractorServiceError(f"Error during metadata extraction from URL: {str(e)}") from e

        return extracted_metadata

    def _extract_metadata_with_crawl4ai(
        self, job_url: str, notion_database_schema: dict[str, Any], model_name: str
    ) -> dict[str, Any]:
        """
        Extract metadata from a job posting URL using Crawl4AI and OpenAI.

        - Retrieves or crawls markdown content for the job posting.
        - Ensures the markdown is uploaded to Notion (creating the page if needed).
        - Extracts structured metadata using OpenAI.
        - Returns metadata including markdown and Notion job/page ID.
        """
        page_id, markdown_content = self._get_or_create_markdown(job_url)

        # Convert Notion schema to OpenAI JSON Schema format
        openai_schema = create_openai_schema_from_notion_database(notion_database_schema, self.add_properties_options)

        # Prepare prompt
        prompt = self._prepare_extraction_prompt(markdown_content)

        # Extract structured metadata
        metadata = self._extract_structured_metadata(
            prompt=prompt,
            model_name=model_name,
            openai_schema=openai_schema,
        )

        # Add markdown and job/page id to metadata
        metadata["markdown_content"] = markdown_content
        metadata["notion_job_id"] = page_id

        # Print the inserted metadata (mimic display_results style)
        print("\n📊 EXTRACTED METADATA:")
        print("-" * 40)
        for key, value in metadata.items():
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            print(f"{key}: {value_str}")

        return metadata

    def _get_or_create_markdown(self, job_url: str) -> tuple[str, str]:
        """
        Retrieve markdown content from Notion if available, otherwise crawl and upload it.
        Returns (page_id, markdown_content).
        """
        settings = get_settings()
        markdown_prop_name = settings.JOB_DESCRIPTION_MARKDOWN_PROPERTY
        notion_page = self.notion_service.find_page_by_url(job_url)
        markdown_content = None
        page_id = None

        if notion_page:
            page_id = str(notion_page.get("id"))
            # Try to retrieve markdown from Notion files property
            markdown_content = self.notion_service.get_file_from_page_property(page_id, markdown_prop_name)

        if not markdown_content:
            markdown_content = self._crawl_markdown(job_url)
            if not page_id:
                # If page does not exist, create it with at least the URL and file property
                url_prop = settings.JOB_URL_PROPERTY_NAME
                properties = {url_prop: {"url": job_url}}
                page = self.notion_service.create_page(properties)
                page_id = str(page.get("id"))

            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / (settings.JOB_DESCRIPTION_MARKDOWN_FILENAME + ".md")
                path.write_text(markdown_content)
                self.notion_service.upload_file_to_page_property(path, page_id, markdown_prop_name)

            # Upload markdown to Notion files property by creating a temp file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, prefix=settings.JOB_DESCRIPTION_MARKDOWN_FILENAME, suffix=".md"
            )
            try:
                temp_file.write(markdown_content.encode("utf-8"))
                temp_file.close()
                self.notion_service.upload_file_to_page_property(temp_file.name, page_id, markdown_prop_name)
            finally:
                try:
                    os.remove(temp_file.name)
                except Exception as e:
                    print(f"Warning: Temporary file {temp_file.name} could not be removed: {e}")

        return str(page_id), markdown_content

    def _crawl_markdown(self, job_url: str) -> str:
        """
        Crawl the given URL asynchronously and return markdown content.
        """

        async def crawl_url_async(url: str) -> str:
            browser_config = self._create_browser_config()
            run_config = self._create_run_config()
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                if not isinstance(result, CrawlResultContainer):
                    raise ExtractorServiceError("Crawl result is not a valid CrawlResult instance")
                if not result.success:
                    raise ExtractorServiceError(f"Failed to crawl URL: {result.error_message}")
                return str(result.markdown)

        return asyncio.run(crawl_url_async(job_url))

    def _prepare_extraction_prompt(self, markdown_content: str) -> str:
        """
        Load and build the extraction prompt from template using the markdown content.
        """
        settings = get_settings()
        prompt_path = settings.PROMPTS_DIRECTORY / settings.EXTRACT_METADATA
        prompt_template = read_file_content(prompt_path)
        return replace_prompt_placeholders(prompt_template, CONTENT=markdown_content)

    def _extract_structured_metadata(
        self, prompt: str, model_name: str, openai_schema: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Use OpenAI for structured metadata extraction.
        """
        return self.openai_client.get_structured_response(
            sys_prompt=prompt,
            user_prompt=None,
            model_name=model_name,
            schema=openai_schema,
            use_web_search=False,
        )

    def _create_browser_config(self, custom_config: dict[str, Any] | None = None) -> BrowserConfig:
        """Create browser configuration with optional customizations.

        Args:
            custom_config: Optional dictionary to override default browser settings

        Returns:
            Configured BrowserConfig instance
        """
        settings = get_settings()

        # Default configuration
        config_params = {
            "headless": settings.CRAWL4AI_HEADLESS,
            "user_agent": settings.CRAWL4AI_USER_AGENT,
            "viewport_width": 1280,
            "viewport_height": 720,
            "verbose": True,
            "text_mode": False,
            "light_mode": False,
        }

        # Apply custom overrides if provided
        if custom_config:
            config_params.update(custom_config)

        return BrowserConfig(**config_params)

    def _create_run_config(self, custom_config: dict[str, Any] | None = None) -> CrawlerRunConfig:
        """Create crawler run configuration with optional customizations.

        Args:
            custom_config: Optional dictionary to override default run settings

        Returns:
            Configured CrawlerRunConfig instance
        """
        settings = get_settings()

        # Default configuration
        config_params = {
            "cache_mode": CacheMode.ENABLED,
            "page_timeout": settings.CRAWL4AI_TIMEOUT_SECONDS * 1000,
            "delay_before_return_html": 2.0,
            "remove_overlay_elements": True,
            "excluded_tags": ["script", "style", "nav", "footer"],
            "only_text": False,
            "word_count_threshold": 10,
            "bypass_cache": False,
            "screenshot": False,
        }

        # Apply custom overrides if provided
        if custom_config:
            config_params.update(custom_config)

        return CrawlerRunConfig(**config_params)
