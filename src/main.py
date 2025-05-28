import argparse
import sys
from typing import Any

from src.common.llm_clients import OpenAIClient
from src.common.notion_service import NotionService
from src.core.config import Settings
from src.core.logger import logger
from src.metadata_extraction.extractor_service import ExtractionMethod, ExtractorService
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
  python src/main.py https://example.com/job --method crawl4ai_plus_gpt
  python src/main.py https://example.com/job --method scrapegraphai_direct --model gpt-4o
        """,
    )

    parser.add_argument("job_url", help="URL of the job posting to analyze")
    parser.add_argument(
        "--model",
        default=default_model,
        help=f"OpenAI model to use for extraction (default: {default_model})",
    )
    parser.add_argument(
        "--method",
        choices=[method.value for method in ExtractionMethod],
        default=ExtractionMethod.OPENAI_WEB_SEARCH.value,
        help=f"Extraction method to use (default: {ExtractionMethod.OPENAI_WEB_SEARCH.value})",
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

        # Get job URL and parameters from parsed arguments
        job_url = args.job_url
        model_name = args.model
        extraction_method = ExtractionMethod(args.method)
        logger.info(f"Processing job URL: {job_url}")
        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Using extraction method: {extraction_method.value}")

        # Fetch database schema from Notion
        logger.info("Fetching Notion database schema...")
        database_schema = notion_service.get_database_schema()
        logger.debug(f"Database schema properties: {list(database_schema.keys())}")

        # Extract metadata from job URL
        logger.info(f"Extracting metadata from job posting using {extraction_method.value}...")
        extracted_metadata = extractor_service.extract_metadata_from_job_url(
            job_url=job_url,
            notion_database_schema=database_schema,
            model_name=model_name,
            extraction_method=extraction_method,
        )
        logger.success("Metadata extraction completed!")

        # Convert to Notion format
        logger.info("Converting to Notion format...")
        notion_update = convert_openai_response_to_notion_update(extracted_metadata, database_schema)

        # Save to Notion database
        logger.info("Saving extracted metadata to Notion database...")
        try:
            saved_page = notion_service.save_or_update_extracted_data(url=job_url, extracted_data=extracted_metadata)
            page_id = saved_page.get("id", "unknown")
            logger.success(f"Successfully saved/updated page in Notion database (ID: {page_id})")
        except Exception as e:
            logger.error(f"Failed to save to Notion database: {str(e)}")
            # Continue execution to show results even if saving fails

        # Display results in CLI
        display_results(extracted_metadata, notion_update, extraction_method)

        logger.success("Job Finder Assistant completed successfully!")

    except Exception as e:
        logger.exception(f"An error occurred during execution: {str(e)}")
        sys.exit(1)


def display_results(
    extracted_metadata: dict[str, Any], notion_update: dict[str, Any], extraction_method: ExtractionMethod
) -> None:
    """Display the extracted metadata and Notion-formatted results in the CLI.

    Args:
        extracted_metadata: The raw extracted metadata from the extraction service
        notion_update: The converted metadata in Notion format
        extraction_method: The extraction method that was used
    """
    print("\n" + "=" * 80)
    print("JOB METADATA EXTRACTION RESULTS")
    print("=" * 80)

    print(f"\n🔧 EXTRACTION METHOD: {extraction_method.value}")
    print("-" * 40)

    print("\n📊 EXTRACTED METADATA:")
    print("-" * 40)
    for key, value in extracted_metadata.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        print(f"{key}: {value_str}")


if __name__ == "__main__":
    main()
