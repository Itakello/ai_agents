import argparse
import sys
from pathlib import Path
from typing import Any

from src.common.llm_clients import OpenAIClient
from src.common.notion_service import NotionService
from src.core.config import Settings
from src.core.logger import logger
from src.metadata_extraction.cache import URLCache
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
        description="Job Finder Assistant - Extract metadata from job postings and export cached content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract metadata from a job URL
  python src/main.py extract https://example.com/job-posting
  python src/main.py extract https://linkedin.com/jobs/view/123456 --model gpt-4o-mini
  python src/main.py extract https://example.com/job --method crawl4ai_plus_gpt

  # Export cached content to PDF
  python src/main.py export-pdf --output-dir ./pdfs
  python src/main.py export-pdf --url https://example.com/job --output-dir ./pdfs

  # List cached URLs
  python src/main.py list-cache
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract metadata from a job URL")
    extract_parser.add_argument("job_url", help="URL of the job posting to analyze")
    extract_parser.add_argument(
        "--model",
        default=default_model,
        help=f"OpenAI model to use for extraction (default: {default_model})",
    )
    extract_parser.add_argument(
        "--method",
        choices=[method.value for method in ExtractionMethod],
        default=ExtractionMethod.CRAWL4AI_PLUS_GPT.value,
        help=f"Extraction method to use (default: {ExtractionMethod.CRAWL4AI_PLUS_GPT.value})",
    )
    extract_parser.add_argument(
        "--add-properties-options",
        action="store_true",
        help="Add options to Notion properties where applicable (e.g., select, multi_select)",
    )

    # Export PDF command
    export_parser = subparsers.add_parser("export-pdf", help="Export cached content to PDF files")
    export_parser.add_argument(
        "--url",
        help="Specific URL to export (if not provided, exports all cached URLs)",
    )
    export_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./exported_pdfs"),
        help="Directory to save PDF files (default: ./exported_pdfs)",
    )

    # List cache command
    subparsers.add_parser("list-cache", help="List all cached URLs")

    return parser.parse_args()


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


def handle_extract_command(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the extract command to extract metadata from a job URL."""
    # Initialize services
    logger.info("Initializing services...")
    openai_client = OpenAIClient(api_key=settings.OPENAI_API_KEY)
    notion_service = NotionService(api_key=settings.NOTION_API_KEY, database_id=settings.NOTION_DATABASE_ID)
    extractor_service = ExtractorService(
        openai_client=openai_client,
        notion_service=notion_service,
        add_properties_options=args.add_properties_options,
    )

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


def handle_export_pdf_command(args: argparse.Namespace) -> None:
    """Handle the export-pdf command to export cached content to PDF files."""
    cache = URLCache()

    try:
        if args.url:
            # Export specific URL
            logger.info(f"Exporting PDF for URL: {args.url}")
            pdf_path = cache.export_to_pdf(args.url, args.output_dir)
            logger.success(f"PDF exported successfully: {pdf_path}")
        else:
            # Export all cached URLs
            logger.info("Exporting all cached URLs to PDF...")
            pdf_paths = cache.export_all_to_pdf(args.output_dir)
            logger.success(f"Exported {len(pdf_paths)} PDFs to {args.output_dir}")
            for path in pdf_paths:
                print(f"  - {path}")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        sys.exit(1)


def handle_list_cache_command() -> None:
    """Handle the list-cache command to list all cached URLs."""
    cache = URLCache()
    cached_urls = cache.list_cached_urls()

    if not cached_urls:
        print("No URLs found in cache.")
        return

    print(f"\nFound {len(cached_urls)} cached URLs:")
    print("=" * 80)

    for i, url_info in enumerate(cached_urls, 1):
        print(f"{i}. {url_info['url']}")
        print(f"   Crawled: {url_info['crawled_at']}")
        print(f"   Size: {url_info['content_size']:,} bytes")
        print()


def main() -> None:
    """Main function for the Job Finder Assistant application."""
    try:
        # Initialize settings first to get default model
        settings = Settings()  # type: ignore[call-arg]
        logger.info("Job Finder Assistant starting...")
        logger.debug(f"Current LOG_LEVEL: {settings.LOG_LEVEL}")

        # Parse command line arguments with settings default model
        args = parse_arguments(default_model=settings.DEFAULT_MODEL_NAME)

        # Handle different commands
        if args.command == "extract":
            handle_extract_command(args, settings)
            logger.success("Job Finder Assistant completed successfully!")
        elif args.command == "export-pdf":
            handle_export_pdf_command(args)
        elif args.command == "list-cache":
            handle_list_cache_command()
        else:
            print("Error: No command specified. Use --help for usage information.")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"An error occurred during execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
