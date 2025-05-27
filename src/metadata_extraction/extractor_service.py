"""
ExtractorService provides core logic for extracting metadata from job descriptions.

This module contains the ExtractorService class which orchestrates the extraction of
structured metadata from job descriptions using OpenAI's language models and
Notion database schemas.
"""

import json
from typing import Any

from ..common.llm_clients import OpenAIClient
from ..common.notion_service import NotionService
from .models import create_openai_schema_from_notion_database


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
        self, job_url: str, notion_database_schema: dict[str, Any], model_name: str
    ) -> dict[str, Any]:
        """Extract structured metadata from a job posting URL.

        Uses OpenAI's web search and structured output capabilities to extract relevant
        information from a job posting URL and structure it according to the provided
        Notion database schema.

        Args:
            job_url: The URL of the job posting to analyze.
            notion_database_schema: The Notion database properties schema for structuring the output.

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
            # Convert Notion schema to OpenAI JSON Schema format
            openai_schema = create_openai_schema_from_notion_database(notion_database_schema)

            # Use OpenAI client with web search and structured outputs
            extracted_data = self.openai_client.extract_structured_data_from_url(
                url=job_url, extraction_schema=openai_schema, model_name=model_name
            )

            return extracted_data

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
