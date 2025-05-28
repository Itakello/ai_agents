import argparse
import json
import sys
from typing import Any

from src.common.llm_clients import OpenAIClient
from src.common.notion_service import NotionService
from src.core.config import Settings
from src.core.logger import logger
from src.metadata_extraction.extractor_service import ExtractorService
from src.metadata_extraction.models import convert_openai_response_to_notion_update


def parse_arguments(default_model: str = "gpt-4o") -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        default_model: Default model name to use if not specified

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Job Finder Assistant - Extract metadata from job postings and format for Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py https://example.com/job-posting
  python src/main.py https://linkedin.com/jobs/view/123456 --model gpt-4o-mini
        """,
    )

    parser.add_argument("job_url", help="URL of the job posting to analyze")
    parser.add_argument(
        "--model",
        default=default_model,
        help=f"OpenAI model to use for extraction (default: {default_model})",
    )

    return parser.parse_args()


def main() -> None:
    """Main function for the Job Finder Assistant application."""
    try:
        # Initialize settings first to get default model
        settings = Settings()  # type: ignore[call-arg]
        logger.info("Job Finder Assistant starting...")
        logger.debug(f"Current LOG_LEVEL: {settings.LOG_LEVEL}")

        # Parse command line arguments with settings default model
        args = parse_arguments(default_model=settings.DEFAULT_MODEL_NAME)

        # Initialize services
        logger.info("Initializing services...")
        openai_client = OpenAIClient(api_key=settings.OPENAI_API_KEY)
        notion_service = NotionService(api_key=settings.NOTION_API_KEY, database_id=settings.NOTION_DATABASE_ID)
        extractor_service = ExtractorService(openai_client=openai_client, notion_service=notion_service)

        # Get job URL from parsed arguments
        job_url = args.job_url
        model_name = args.model
        logger.info(f"Processing job URL: {job_url}")
        logger.debug(f"Using model: {model_name}")

        # Fetch database schema from Notion
        logger.info("Fetching Notion database schema...")
        database_schema = notion_service.get_database_schema()
        logger.debug(f"Database schema properties: {list(database_schema.keys())}")

        # Extract metadata from job URL
        logger.info("Extracting metadata from job posting...")
        extracted_metadata = extractor_service.extract_metadata_from_job_url(
            job_url=job_url, notion_database_schema=database_schema, model_name=model_name
        )
        logger.success("Metadata extraction completed!")

        # Convert to Notion format
        logger.info("Converting to Notion format...")
        notion_update = convert_openai_response_to_notion_update(extracted_metadata, database_schema)

        # Display results in CLI
        display_results(extracted_metadata, notion_update)

        logger.success("Job Finder Assistant completed successfully!")

    except Exception as e:
        logger.exception(f"An error occurred during execution: {str(e)}")
        sys.exit(1)


def display_results(extracted_metadata: dict[str, Any], notion_update: dict[str, Any]) -> None:
    """Display the extracted metadata and Notion-formatted results in the CLI.

    Args:
        extracted_metadata: The raw extracted metadata from OpenAI
        notion_update: The converted metadata in Notion format
    """
    print("\n" + "=" * 80)
    print("JOB METADATA EXTRACTION RESULTS")
    print("=" * 80)

    print("\n📊 EXTRACTED METADATA:")
    print("-" * 40)
    for key, value in extracted_metadata.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        print(f"{key}: {value_str}")

    print("\n🔄 NOTION FORMAT:")
    print("-" * 40)
    print(json.dumps(notion_update, indent=2, ensure_ascii=False))

    print("\n✅ Ready for Notion database insertion!")
    print("=" * 80)


if __name__ == "__main__":
    main()
