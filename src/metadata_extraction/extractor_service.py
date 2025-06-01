"""
ExtractorService provides core logic for extracting metadata from job descriptions.

This module contains the ExtractorService class which orchestrates the extraction of
structured metadata from job descriptions using OpenAI's language models and
Notion database schemas.
"""

import asyncio
from enum import Enum
from typing import Any

from crawl4ai import AsyncWebCrawler  # type: ignore
from crawl4ai.async_configs import BrowserConfig, CacheMode, CrawlerRunConfig  # type: ignore
from crawl4ai.models import CrawlResultContainer  # type: ignore

from ..common.llm_clients import OpenAIClient
from ..common.notion_service import NotionService
from ..common.utils import read_file_content, replace_prompt_placeholders
from ..core.config import get_settings
from .cache import URLCache
from .models import create_openai_schema_from_notion_database


class ExtractionMethod(Enum):
    """Available extraction methods."""

    OPENAI_WEB_SEARCH = "openai_web_search"
    CRAWL4AI_PLUS_GPT = "crawl4ai_plus_gpt"


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
        self.url_cache = URLCache()

    def extract_metadata_from_job_url(
        self,
        job_url: str,
        notion_database_schema: dict[str, Any],
        model_name: str,
        extraction_method: ExtractionMethod = ExtractionMethod.OPENAI_WEB_SEARCH,
    ) -> dict[str, Any]:
        """Extract structured metadata from a job posting URL.

        Args:
            job_url: The URL of the job posting to analyze.
            notion_database_schema: The Notion database properties schema for structuring the output.
            model_name: The name of the OpenAI model to use.
            extraction_method: The extraction method to use.

        Returns:
            A dictionary containing the extracted metadata in a format compatible with OpenAI's
            structured output, ready for conversion to Notion format.

        Raises:
            ExtractorServiceError: If there's an error during the extraction process.
        """
        if not job_url.strip():
            raise ExtractorServiceError("Job URL cannot be empty")

        if not notion_database_schema:
            raise ExtractorServiceError("Notion database schema cannot be empty")

        try:
            if extraction_method == ExtractionMethod.OPENAI_WEB_SEARCH:
                return self._extract_with_openai_web_search(job_url, notion_database_schema, model_name)
            elif extraction_method == ExtractionMethod.CRAWL4AI_PLUS_GPT:
                return self._extract_with_crawl4ai_plus_gpt(job_url, notion_database_schema, model_name)
            else:
                raise ExtractorServiceError(f"Unsupported extraction method: {extraction_method}")

        except Exception as e:
            if isinstance(e, ExtractorServiceError):
                raise
            raise ExtractorServiceError(f"Error during metadata extraction from URL: {str(e)}") from e

    def _extract_with_openai_web_search(
        self, job_url: str, notion_database_schema: dict[str, Any], model_name: str
    ) -> dict[str, Any]:
        """Extract metadata using OpenAI's web search capabilities."""
        # Convert Notion schema to OpenAI JSON Schema format
        openai_schema = create_openai_schema_from_notion_database(notion_database_schema, self.add_properties_options)

        # Load the prompt from file using configured paths
        settings = get_settings()
        prompt_path = settings.PROMPTS_DIRECTORY / settings.METADATA_EXTRACTION_PROMPT_FILE
        sys_prompt_template = read_file_content(prompt_path)
        sys_prompt = replace_prompt_placeholders(sys_prompt_template, URL=job_url)

        return self.openai_client.get_structured_response(
            sys_prompt=sys_prompt,
            user_prompt=None,
            model_name=model_name,
            schema=openai_schema,
            use_web_search=True,
        )

    def _extract_with_crawl4ai_plus_gpt(
        self, job_url: str, notion_database_schema: dict[str, Any], model_name: str
    ) -> dict[str, Any]:
        """Extract metadata using Crawl4AI for crawling + GPT for extraction."""

        # Check cache first
        cached_content = self.url_cache.get_cached_content(job_url)
        if cached_content:
            markdown_content = cached_content
        else:
            # Crawl the URL to get markdown content using async crawler
            async def crawl_url_async(url: str) -> str:
                # Create configurations using the helper methods
                browser_config = self._create_browser_config()
                run_config = self._create_run_config()

                async with AsyncWebCrawler(config=browser_config) as crawler:
                    result = await crawler.arun(url=url, config=run_config)
                    if not isinstance(result, CrawlResultContainer):
                        raise ExtractorServiceError("Crawl result is not a valid CrawlResult instance")
                    # Handle the result properly by accessing its attributes with type: ignore
                    if not result.success:
                        raise ExtractorServiceError(f"Failed to crawl URL: {result.error_message}")

                    return str(result.markdown)

            # Run the async crawler
            markdown_content = asyncio.run(crawl_url_async(job_url))

            # Cache the crawled content
            self.url_cache.cache_content(job_url, markdown_content)

        # Convert Notion schema to OpenAI JSON Schema format
        openai_schema = create_openai_schema_from_notion_database(notion_database_schema, self.add_properties_options)

        # Load and build prompt from template using configured paths
        settings = get_settings()
        prompt_path = settings.PROMPTS_DIRECTORY / settings.CRAWL4AI_PROMPT_FILE
        prompt_template = read_file_content(prompt_path)
        prompt = replace_prompt_placeholders(prompt_template, CONTENT=markdown_content)

        # Use OpenAI for structured extraction
        return self.openai_client.get_structured_response(
            sys_prompt=None,
            user_prompt=prompt,
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
