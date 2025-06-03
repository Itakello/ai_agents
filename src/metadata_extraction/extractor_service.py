"""
ExtractorService provides core logic for extracting metadata from job descriptions.

This module contains the ExtractorService class which orchestrates the extraction of
structured metadata from job descriptions using OpenAI's language models and
Notion database schemas.
"""

import asyncio
import uuid
from typing import Any

import requests
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

        # --- Add job ID to extracted metadata ---
        if extracted_metadata is not None:
            if "ID" not in extracted_metadata or not extracted_metadata["ID"]:
                extracted_metadata["ID"] = str(uuid.uuid4())
        return extracted_metadata

    def _extract_metadata_with_crawl4ai(
        self, job_url: str, notion_database_schema: dict[str, Any], model_name: str
    ) -> dict[str, Any]:
        """Extract metadata using Crawl4AI for crawling + GPT for extraction."""

        # Try to get markdown content from Notion DB property 'Job Description Markdown'
        notion_page = self.notion_service.find_page_by_url(job_url)
        markdown_content = None
        page_id = None
        if notion_page:
            page_id = notion_page.get("id")
            properties = notion_page.get("properties", {})
            jd_markdown_prop = properties.get("Job Description Markdown")
            if jd_markdown_prop:
                # Notion file property format
                files = jd_markdown_prop.get("files", [])
                if files and isinstance(files, list):
                    file_url = files[0].get("file", {}).get("url") or files[0].get("external", {}).get("url")
                    if file_url:
                        resp = requests.get(file_url)
                        if resp.ok:
                            markdown_content = resp.text
        if not markdown_content:
            # Crawl the URL to get markdown content using async crawler
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

            markdown_content = asyncio.run(crawl_url_async(job_url))
            # Save markdown content to Notion DB file property
            import os
            import tempfile
            from pathlib import Path

            if not page_id:
                # If page does not exist, create it with at least the URL and file property
                schema = self.notion_service.get_database_schema()
                url_prop = self.notion_service._find_url_property_name(schema)
                properties = {
                    (url_prop or "URL"): {"url": job_url},
                    "Job Description Markdown": {"files": []},
                }
                page = self.notion_service.create_page(properties)
                page_id = str(page.get("id"))
            # Write markdown to temp file and upload
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as tmp_md:
                tmp_md.write(markdown_content)
                tmp_md_path = Path(tmp_md.name)
            self.notion_service.upload_file_to_page_property(page_id, "Job Description Markdown", tmp_md_path)
            os.remove(tmp_md_path)

        # Convert Notion schema to OpenAI JSON Schema format
        openai_schema = create_openai_schema_from_notion_database(notion_database_schema, self.add_properties_options)

        # Load and build prompt from template using configured paths
        settings = get_settings()
        prompt_path = settings.PROMPTS_DIRECTORY / settings.EXTRACT_METADATA
        prompt_template = read_file_content(prompt_path)
        prompt = replace_prompt_placeholders(prompt_template, CONTENT=markdown_content)

        # Use OpenAI for structured extraction
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
