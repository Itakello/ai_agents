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
        description="AI Agents for Notion – A multi-agent toolkit (currently ships with the Resume Tailoring agent)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ------------------------------------------------------------------
    # Top-level: *agent* selection
    # ------------------------------------------------------------------
    agents_sub = parser.add_subparsers(dest="agent", required=True, help="Available AI agents")

    # --------------------------- RESUME AGENT --------------------------
    resume_parser = agents_sub.add_parser("resume", help="Resume tailoring agent")

    resume_sub = resume_parser.add_subparsers(dest="command", required=True, help="Resume agent commands")

    # Extract command
    extract_parser = resume_sub.add_parser("extract", help="Extract metadata from a job URL")
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
    tailor_parser = resume_sub.add_parser("tailor", help="Tailor resume for a specific job")
    tailor_parser.add_argument(
        "job_url",
        type=str,
        help="Job posting URL (matches the URL property in Notion DB)",
    )

    # Init command – verifies and patches the Notion DB schema
    resume_sub.add_parser("init", help="Initialise / repair the Notion database schema")

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


async def handle_init_command(settings: Settings) -> None:
    """Verify and patch the Notion database so that all required properties are present."""

    logger.info("Verifying Notion database schema – this may take a few seconds …")

    notion_service = NotionSyncService(database_id=settings.NOTION_DATABASE_ID)

    try:
        await notion_service._ensure_required_properties()
    except Exception as e:  # pragma: no cover – surface any unexpected errors
        logger.error(f"Failed to initialise database schema: {str(e)}")
        sys.exit(1)

    logger.success("Database schema verified and up-to-date ✔️")


async def handle_extract_command(args: argparse.Namespace, settings: Settings) -> dict[str, Any]:
    """Handle the extract command: pull metadata from a job URL and persist it in Notion (fully async)."""

    # ------------------------------------------------------------------
    # 1. Initialise services
    # ------------------------------------------------------------------
    logger.info("Initializing services...")

    openai_service = OpenAIService(api_key=settings.OPENAI_API_KEY)

    notion_service = NotionSyncService(database_id=settings.NOTION_DATABASE_ID)

    # Verify database schema first – we do **not** attempt to patch here.
    if not await notion_service.is_database_verified():
        logger.error("Notion database schema is incomplete or invalid. Run `python src/main.py init` first.")
        sys.exit(2)

    # The synchronous schema check performed during initialisation closes
    # its temporary event-loop, leaving the internal client orphaned.  Create
    # a *fresh* API service bound to the current asynchronous loop.
    from src.common.services.notion_api_service import NotionAPIService  # local import to avoid cycle

    notion_service.api_service = NotionAPIService()

    extractor_service = ExtractorService(
        openai_service=openai_service,
        notion_service=notion_service,
        add_properties_options=args.add_properties_options,
    )

    # ------------------------------------------------------------------
    # 2. Fetch the (already verified) database schema for the extractor
    #    – no automatic patching here.
    database_schema = notion_service.get_database_schema()

    # ------------------------------------------------------------------
    # 3. Extract metadata using the (potentially blocking) extractor – keep
    #    this call sync since it may use OpenAI in a blocking fashion.
    # ------------------------------------------------------------------
    try:
        # Run the (blocking) extraction inside a worker thread so that we
        # do not attempt to start a new event-loop while the current one
        # is already running.
        extracted_metadata = await asyncio.to_thread(
            extractor_service.extract_metadata_from_job_url,
            args.job_url,
            database_schema,
            args.model,
        )
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Persist results back to Notion
    # ------------------------------------------------------------------
    try:
        await notion_service.save_or_update_extracted_data(
            settings.NOTION_DATABASE_ID,
            args.job_url,
            extracted_metadata,
        )
        logger.success(f"Saved/updated job metadata for URL: {args.job_url}")
    except Exception as e:
        logger.error(f"Failed to save to Notion database: {str(e)}")

    return extracted_metadata


async def handle_tailor_resume_command(args: argparse.Namespace, settings: Settings) -> None:
    """Handle the `resume tailor` command to tailor the resume for a specific job using Notion only."""

    # Initialize services for resume tailoring...
    logger.info("Initializing services for resume tailoring...")
    openai_service = OpenAIService(api_key=settings.OPENAI_API_KEY)
    notion_service = NotionSyncService(database_id=settings.NOTION_DATABASE_ID)

    # Verify database schema – exit early if not valid.
    if not await notion_service.is_database_verified():
        logger.error("Notion database schema is incomplete or invalid. Run `python src/main.py init` first.")
        sys.exit(2)

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

        # Dispatch based on selected agent & command
        if args.agent == "resume" and args.command == "extract":
            job_metadata = asyncio.run(handle_extract_command(args, settings))
            display_results(job_metadata)
        elif args.agent == "resume" and args.command == "tailor":
            asyncio.run(handle_tailor_resume_command(args, settings))
        elif args.agent == "resume" and args.command == "init":
            asyncio.run(handle_init_command(settings))
        else:
            print("Error: Invalid command. Use --help for usage information.")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"An error occurred during execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
