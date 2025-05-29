"""
ExtractorService provides core logic for extracting metadata from job descriptions.

This module contains the ExtractorService class which orchestrates the extraction of
structured metadata from job descriptions using OpenAI's language models and
Notion database schemas.
"""

import asyncio
import json
from enum import Enum
from pathlib import Path
from typing import Any

from crawl4ai import AsyncWebCrawler  # type: ignore
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig  # type: ignore
from crawl4ai.models import CrawlResult  # type: ignore

from ..common.llm_clients import OpenAIClient
from ..common.notion_service import NotionService
from ..common.utils import read_file_content
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

    def __init__(self, openai_client: OpenAIClient, notion_service: NotionService) -> None:
        """Initialize the ExtractorService with required clients.

        Args:
            openai_client: An initialized OpenAI client for LLM interactions.
            notion_service: An initialized Notion service for database operations.
        """
        self.openai_client = openai_client
        self.notion_service = notion_service

    def extract_metadata_from_job_description(
        self, job_description: str, notion_database_schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract structured metadata from a job description text.

        Uses OpenAI's language models to extract relevant information from a job description
        and structure it according to the provided Notion database schema.

        Args:
            job_description: The job description text to analyze.
            notion_database_schema: The Notion database properties schema for structuring the output.

        Returns:
            A dictionary containing the extracted metadata structured according to the schema.

        Raises:
            ExtractorServiceError: If there's an error during the extraction process.
        """
        if not job_description.strip():
            raise ExtractorServiceError("Job description text cannot be empty")

        if not notion_database_schema:
            raise ExtractorServiceError("Notion database schema cannot be empty")

        try:
            # Convert Notion schema to OpenAI JSON Schema format
            openai_schema = create_openai_schema_from_notion_database(notion_database_schema)

            # Build the extraction prompt
            prompt = self._build_extraction_prompt(job_description, notion_database_schema, openai_schema)

            # Get completion from OpenAI
            response = self.openai_client.get_response(
                sys_prompt=None, user_prompt=prompt, model_name="gpt-4-1106-preview"
            )

            # Parse the JSON response
            try:
                extracted_data = json.loads(response)
            except json.JSONDecodeError as e:
                raise ExtractorServiceError(f"Failed to parse LLM response as JSON: {str(e)}") from e

            # Validate that response is a dictionary
            if not isinstance(extracted_data, dict):
                raise ExtractorServiceError("LLM response is not a valid JSON object")

            return extracted_data

        except Exception as e:
            if isinstance(e, ExtractorServiceError):
                raise
            raise ExtractorServiceError(f"Error during metadata extraction: {str(e)}") from e

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

    def _build_extraction_prompt(
        self, job_description: str, notion_schema: dict[str, Any], openai_schema: dict[str, Any]
    ) -> str:
        """Build the prompt for extracting metadata from job description.

        Args:
            job_description: The job description text.
            notion_schema: The Notion database schema.
            openai_schema: The OpenAI JSON schema.

        Returns:
            The constructed prompt string.
        """
        # Filter out read-only properties
        read_only_types = {"created_time", "last_edited_time", "formula", "rollup"}
        editable_schema = {
            name: props for name, props in notion_schema.items() if props.get("type") not in read_only_types
        }

        # Build field descriptions
        field_descriptions = []
        for field_name, field_props in editable_schema.items():
            field_type = field_props.get("type", "unknown")
            if field_type == "multi_select" and "multi_select" in field_props:
                options = [opt["name"] for opt in field_props["multi_select"].get("options", [])]
                desc = f"{field_name}: array (array of options: {', '.join(options)})"
            elif field_type == "select" and "select" in field_props:
                options = [opt["name"] for opt in field_props["select"].get("options", [])]
                desc = f"{field_name}: string (options: {', '.join(options)})"
            elif field_type == "status" and "status" in field_props:
                options = [opt["name"] for opt in field_props["status"].get("options", [])]
                desc = f"{field_name}: string (options: {', '.join(options)})"
            elif field_type == "title":
                desc = f"{field_name}: string"
            elif field_type == "rich_text":
                desc = f"{field_name}: string"
            elif field_type == "number":
                desc = f"{field_name}: number"
            elif field_type == "checkbox":
                desc = f"{field_name}: boolean"
            elif field_type == "date":
                desc = f"{field_name}: string (YYYY-MM-DD format)"
            elif field_type == "email":
                desc = f"{field_name}: string (email format)"
            elif field_type == "url":
                desc = f"{field_name}: string (URL format)"
            else:
                desc = f"{field_name}: {field_type}"

            field_descriptions.append(desc)

        prompt = f"""You are an expert at analyzing job descriptions and extracting structured metadata.

Extract relevant information from the following job description and return it as a JSON object that matches the specified schema.

Job Description:
{job_description}

Available Fields:
{chr(10).join(field_descriptions)}

Instructions:
- Only extract information that is clearly present in the job description
- Return a valid JSON object only
- Use null for missing information
- For multi-select fields, return an array of strings
- For date fields, use YYYY-MM-DD format
- For salary/number fields, extract numeric values when possible

JSON Schema for validation:
{json.dumps(openai_schema, indent=2)}

Return only the JSON object, no additional text or formatting."""

        return prompt

    def _extract_with_openai_web_search(
        self, job_url: str, notion_database_schema: dict[str, Any], model_name: str
    ) -> dict[str, Any]:
        """Extract metadata using OpenAI's web search capabilities."""
        # Convert Notion schema to OpenAI JSON Schema format
        openai_schema = create_openai_schema_from_notion_database(notion_database_schema)

        # Load the prompt from file
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "sys_prompt_extract_metadata.txt"
        sys_prompt_template = read_file_content(prompt_path)
        sys_prompt = sys_prompt_template.replace("{{URL}}", job_url)

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

        # Crawl the URL to get markdown content using async crawler
        async def crawl_url_async(url: str) -> str:
            browser_config = BrowserConfig()  # Default browser configuration
            run_config = CrawlerRunConfig()  # Default crawl run configuration

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                if not isinstance(result, CrawlResult):
                    raise ExtractorServiceError("Crawl result is not a valid CrawlResult instance")
                # Handle the result properly by accessing its attributes with type: ignore
                if not result.success:
                    raise ExtractorServiceError(f"Failed to crawl URL: {result.error_message}")

                return str(result.markdown)

        # Run the async crawler
        markdown_content = asyncio.run(crawl_url_async(job_url))

        # Convert Notion schema to OpenAI JSON Schema format
        openai_schema = create_openai_schema_from_notion_database(notion_database_schema)

        # Load and build prompt from template
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "crawl4ai_plus_gpt_prompt.txt"
        prompt_template = read_file_content(prompt_path)
        prompt = prompt_template.replace("{{CONTENT}}", markdown_content)

        # Use OpenAI for structured extraction
        return self.openai_client.get_structured_response(
            sys_prompt=None,
            user_prompt=prompt,
            model_name=model_name,
            schema=openai_schema,
            use_web_search=False,
        )

    def _build_field_descriptions(self, schema: dict[str, Any]) -> list[str]:
        """Build field descriptions from Notion schema."""
        # Filter out read-only properties
        read_only_types = {"created_time", "last_edited_time", "formula", "rollup"}
        editable_schema = {name: props for name, props in schema.items() if props.get("type") not in read_only_types}

        field_descriptions = []
        for field_name, field_props in editable_schema.items():
            field_type = field_props.get("type", "unknown")
            if field_type == "multi_select" and "multi_select" in field_props:
                options = [opt["name"] for opt in field_props["multi_select"].get("options", [])]
                desc = f"{field_name}: array (array of options: {', '.join(options)})"
            elif field_type == "select" and "select" in field_props:
                options = [opt["name"] for opt in field_props["select"].get("options", [])]
                desc = f"{field_name}: string (options: {', '.join(options)})"
            elif field_type == "status" and "status" in field_props:
                options = [opt["name"] for opt in field_props["status"].get("options", [])]
                desc = f"{field_name}: string (options: {', '.join(options)})"
            elif field_type == "title":
                desc = f"{field_name}: string"
            elif field_type == "rich_text":
                desc = f"{field_name}: string"
            elif field_type == "number":
                desc = f"{field_name}: number"
            elif field_type == "checkbox":
                desc = f"{field_name}: boolean"
            elif field_type == "date":
                desc = f"{field_name}: string (YYYY-MM-DD format)"
            elif field_type == "email":
                desc = f"{field_name}: string (email format)"
            elif field_type == "url":
                desc = f"{field_name}: string (URL format)"
            else:
                desc = f"{field_name}: {field_type}"

            field_descriptions.append(desc)

        return field_descriptions
