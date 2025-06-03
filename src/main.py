import argparse
import sys
from pathlib import Path
from typing import Any

from src.common.llm_clients import OpenAIClient
from src.common.notion_service import NotionService
from src.core.config import Settings
from src.core.logger import logger
from src.metadata_extraction.extractor_service import ExtractorService
from src.metadata_extraction.models import convert_openai_response_to_notion_update
from src.resume_tailoring.latex_service import LatexService
from src.resume_tailoring.pdf_compiler import PDFCompiler
from src.resume_tailoring.tailor_service import TailorService


def parse_arguments(default_model: str = "gpt-4o") -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        default_model: Default model name to use if not specified

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Job Finder Assistant - Extract metadata from job postings and store all data in Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract metadata from a job URL
  python src/main.py extract https://example.com/job-posting
  python src/main.py extract https://linkedin.com/jobs/view/123456 --model gpt-4o-mini

  # Tailor resume for a specific job
  python src/main.py tailor-resume --job-id abc123 --output-stem company-role
  python src/main.py tailor-resume --job-id abc123 --output-stem company-role --diff
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract metadata from a job URL")
    extract_parser.add_argument("job_url", help="URL of the job posting to analyze")
    extract_parser.add_argument(
        "--model",
        default=default_model,
        help=f"OpenAI model to use for extraction (default: {default_model})",
    )

    extract_parser.add_argument(
        "--add-properties-options",
        action="store_true",
        help="Add options to Notion properties where applicable (e.g., select, multi_select)",
    )

    # Tailor resume command
    tailor_parser = subparsers.add_parser("tailor-resume", help="Tailor resume for a specific job")
    tailor_parser.add_argument("--job-id", required=True, help="Job ID (matches the 'ID' property in Notion DB)")
    tailor_parser.add_argument("--output-stem", required=True, help="Output filename stem for generated files")

    return parser.parse_args()


def display_results(extracted_metadata: dict[str, Any], notion_update: dict[str, Any]) -> None:
    """Display the extracted metadata and Notion-formatted results in the CLI.

    Args:
        extracted_metadata: The raw extracted metadata from the extraction service
        notion_update: The converted metadata in Notion format
    """

    print("\n📊 EXTRACTED METADATA:")
    print("-" * 40)
    for key, value in extracted_metadata.items():
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        print(f"{key}: {value_str}")


def handle_extract_command(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the extract command to extract metadata from a job URL and save everything in Notion."""
    # Initialize services
    logger.info("Initializing services...")
    openai_client = OpenAIClient(api_key=settings.OPENAI_API_KEY)
    notion_service = NotionService(api_key=settings.NOTION_API_KEY, database_id=settings.NOTION_DATABASE_ID)
    extractor_service = ExtractorService(
        openai_client=openai_client,
        notion_service=notion_service,
        add_properties_options=args.add_properties_options,
    )

    # Fetch Notion DB schema
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

    # Convert extracted metadata to Notion format
    notion_update = convert_openai_response_to_notion_update(extracted_metadata, database_schema)

    # Save to Notion
    try:
        notion_service.save_or_update_extracted_data(
            args.job_url,
            notion_update,
        )
        logger.success(f"Saved/updated job metadata for URL: {args.job_url}")
    except Exception as e:
        logger.error(f"Failed to save to Notion database: {str(e)}")

    # Display results in CLI
    display_results(extracted_metadata, notion_update)


def handle_tailor_resume_command(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the tailor-resume command to tailor resume for a specific job using Notion only."""
    # Initialize services for resume tailoring...
    logger.info("Initializing services for resume tailoring...")
    openai_client = OpenAIClient(api_key=settings.OPENAI_API_KEY)
    notion_service = NotionService(api_key=settings.NOTION_API_KEY, database_id=settings.NOTION_DATABASE_ID)
    pdf_compiler = PDFCompiler()
    latex_service = LatexService(pdf_compiler=pdf_compiler, settings=settings)
    tailor_service = TailorService(
        openai_client=openai_client,
        latex_service=latex_service,
        notion_service=notion_service,
    )

    job_id = args.job_id
    output_stem = args.output_stem

    # Fetch job metadata and markdown from Notion
    try:
        logger.info("Fetching job information from Notion using job_id...")
        page_content = notion_service.find_page_by_job_id(job_id)
        if not page_content:
            logger.error(f"No Notion page found for job_id: {job_id}")
            sys.exit(1)

        job_metadata = {}
        markdown_content = None
        if "properties" in page_content:
            for prop_name, prop_value in page_content["properties"].items():
                if prop_value.get("type") == "title":
                    title_texts = prop_value.get("title", [])
                    if title_texts:
                        job_metadata[prop_name] = "".join([t.get("plain_text", "") for t in title_texts])
                elif prop_value.get("type") == "rich_text":
                    rich_texts = prop_value.get("rich_text", [])
                    if rich_texts:
                        # If this is the markdown property, extract it
                        if prop_name.lower() in [
                            "job description markdown",
                            "markdown",
                            "job markdown",
                            "job description",
                        ]:
                            markdown_content = "".join([t.get("plain_text", "") for t in rich_texts])
                        job_metadata[prop_name] = "".join([t.get("plain_text", "") for t in rich_texts])
                elif prop_value.get("type") == "select":
                    select_value = prop_value.get("select")
                    if select_value:
                        job_metadata[prop_name] = select_value.get("name", "")
                elif prop_value.get("type") == "url":
                    url_value = prop_value.get("url")
                    if url_value:
                        job_metadata[prop_name] = url_value

        if not markdown_content:
            logger.error("No job description found in Notion for this job_id")
            sys.exit(1)

        # Read master resume content
        logger.info("Reading master resume content...")
        master_resume_path = Path(settings.MASTER_RESUME_PATH)
        if not master_resume_path.exists():
            logger.error(f"Master resume file not found: {master_resume_path}")
            sys.exit(1)

        master_resume_content = master_resume_path.read_text(encoding="utf-8")

        # Call tailor service
        logger.info("Tailoring resume...")
        tailor_service.tailor_resume(
            job_metadata=job_metadata,
            master_resume_tex_content=master_resume_content,
            notion_page_id=settings.NOTION_DATABASE_ID,
            output_filename_stem=output_stem,
        )

        logger.success("Resume tailoring completed successfully!")
        logger.info(f"Tailored resume saved with stem: {output_stem}")
        logger.info(f"Diff PDF generated with stem: {output_stem}")

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

        # Parse command line arguments with settings default model
        args = parse_arguments(default_model=settings.DEFAULT_MODEL_NAME)

        # Handle different commands
        if args.command == "extract":
            handle_extract_command(args, settings)
            logger.success("Job Finder Assistant completed successfully!")
        elif args.command == "tailor-resume":
            handle_tailor_resume_command(args, settings)
        else:
            print("Error: No command specified. Use --help for usage information.")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"An error occurred during execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
