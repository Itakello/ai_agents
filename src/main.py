import argparse
import asyncio
import sys
from typing import Any

from src.common.services import NotionSyncService, OpenAIService
from src.core.config import Settings
from src.core.logger import logger
from src.metadata_extraction import ExtractorService
from src.resume_tailoring import LatexService, PDFCompiler, TailorService


def parse_arguments(default_model: str) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        default_model: Default model name to use if not specified

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Job Finder Assistant - Extract metadata from job postings and store all data in Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Extract metadata from a job URL
  python src/main.py extract https://example.com/job-posting
  python src/main.py extract https://linkedin.com/jobs/view/123456 --model gpt-4o-mini

  # Tailor resume for a specific job
  python src/main.py tailor-resume https://example.com/job-posting
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract metadata from a job URL")
    extract_parser.add_argument(
        "job_url",
        type=str,
        help="URL of the job posting to analyze",
    )
    extract_parser.add_argument(
        "--model",
        default=default_model,
        type=str,
        help=f"OpenAI model to use for extraction (default: {default_model})",
    )

    extract_parser.add_argument(
        "--add-properties-options",
        default=False,
        type=bool,
        help="Add options to Notion properties where applicable (e.g., select, multi_select)",
    )

    # Tailor resume command
    tailor_parser = subparsers.add_parser("tailor-resume", help="Tailor resume for a specific job")
    tailor_parser.add_argument(
        "job_url",
        type=str,
        help="Job posting URL (matches the URL property in Notion DB)",
    )

    return parser.parse_args()


def display_results(extracted_metadata: dict[str, Any]) -> None:
    """Display the extracted metadata and Notion-formatted results in the CLI.

    Args:
        extracted_metadata: The raw extracted metadata from the extraction service
    """

    print("\n📊 EXTRACTED METADATA:")
    print("-" * 40)
    for key, value in extracted_metadata.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        print(f"{key}: {value_str}")


def handle_extract_command(args: argparse.Namespace, settings: Settings) -> dict[str, Any]:
    """Handle the extract command to extract metadata from a job URL and save everything in Notion."""
    # Initialize services
    logger.info("Initializing services...")
    openai_service = OpenAIService(api_key=settings.OPENAI_API_KEY)
    notion_service = NotionSyncService(database_id=settings.NOTION_DATABASE_ID)
    extractor_service = ExtractorService(
        openai_service=openai_service,
        notion_service=notion_service,
        add_properties_options=args.add_properties_options,
    )

    # Retrieve the Notion database schema (converted to raw dict) synchronously
    database_schema = notion_service.get_database_schema()

    # Extract metadata from job URL
    try:
        extracted_metadata = extractor_service.extract_metadata_from_job_url(
            args.job_url,
            database_schema,
            args.model,
        )
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        sys.exit(1)

    # Save to Notion
    try:
        asyncio.run(
            notion_service.save_or_update_extracted_data(
                settings.NOTION_DATABASE_ID,
                args.job_url,
                extracted_metadata,
            )
        )
        logger.success(f"Saved/updated job metadata for URL: {args.job_url}")
    except Exception as e:
        logger.error(f"Failed to save to Notion database: {str(e)}")

    return extracted_metadata


async def handle_tailor_resume_command(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the tailor-resume command to tailor resume for a specific job using Notion only."""

    # Initialize services for resume tailoring...
    logger.info("Initializing services for resume tailoring...")
    openai_service = OpenAIService(api_key=settings.OPENAI_API_KEY)
    notion_service = NotionSyncService(database_id=settings.NOTION_DATABASE_ID)
    pdf_compiler = PDFCompiler()
    latex_service = LatexService(pdf_compiler=pdf_compiler, settings=settings)
    tailor_service = TailorService(
        openai_service=openai_service,
        latex_service=latex_service,
        notion_service=notion_service,
    )

    try:
        job_page = await notion_service.find_page_by_url(args.job_url)

        if job_page is None:
            logger.error("Failed to locate or create job metadata in Notion.")
            sys.exit(1)

        # Read master resume content
        logger.info("Reading master resume content...")
        master_resume_path = settings.MASTER_RESUME_PATH

        if not master_resume_path.exists():
            logger.error(f"Master resume file not found: {master_resume_path}")
            sys.exit(1)

        master_resume_tex_content = master_resume_path.read_text(encoding="utf-8")

        # Call tailor service
        logger.info("Tailoring resume...")
        if isinstance(job_page, dict):
            job_metadata_dump = job_page  # Fixture / mock returning plain dict
            page_id = job_page.get("id", "unknown")
        else:
            job_metadata_dump = job_page.model_dump()
            page_id = job_page.id

        # Call may be a coroutine or regular function (for easier mocking in tests)
        result = tailor_service.tailor_resume(
            job_metadata=job_metadata_dump,
            master_resume_tex_content=master_resume_tex_content,
            notion_page_id=page_id,
        )

        if asyncio.iscoroutine(result):
            await result

        logger.success("Resume tailoring completed successfully!")

    except Exception as e:
        logger.error(f"Error during resume tailoring: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main function for the Job Finder Assistant application."""
    try:
        # Initialize settings first to get default model
        settings = Settings()  # type: ignore[call-arg]
        logger.info("Job Finder Assistant starting...")
        logger.debug(f"Current LOG_LEVEL: {settings.LOG_LEVEL}")

        # Parse command line arguments with settings default model5
        args = parse_arguments(default_model=settings.DEFAULT_MODEL_NAME)

        # Handle different commands
        if args.command == "extract":
            job_metadata = handle_extract_command(args, settings)
            display_results(job_metadata)
        elif args.command == "tailor-resume":
            asyncio.run(handle_tailor_resume_command(args, settings))
        else:
            print("Error: No command specified. Use --help for usage information.")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"An error occurred during execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
