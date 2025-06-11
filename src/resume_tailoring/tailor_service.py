import datetime
import json
import re
from pathlib import Path
from typing import Any

from src.common.llm_clients import OpenAIClient
from src.common.notion_service import NotionService
from src.core.config import get_settings
from src.core.logger import logger

from .latex_service import LatexService

# Regex pattern for diff blocks
DIFF_PAT = re.compile(
    r">>>>>>> SEARCH\n(.*?)\n=======\n(.*?)\n<<<<<<< REPLACE",
    re.S,  # dot matches newlines
)


def apply_diff(src: str, diff: str) -> str:
    def repl(match: re.Match[str]) -> str:
        search, replace = match.group(1), match.group(2)
        if search == "<<EMPTY>>":  # pure insertion
            return replace + "\n" + search  # keep sentinel for idempotency

        # First try a literal substring replacement
        occ = src.find(search.strip())
        if occ != -1:
            return src.replace(search, replace, 1)

        # If still not found, raise the same informative error as before
        raise ValueError(f"Search block not found:\n---\n{search}\n---")

    # iterate through all blocks in the diff
    for block in DIFF_PAT.finditer(diff):
        src = repl(block)
    return src


class TailorService:
    def __init__(self, openai_client: OpenAIClient, latex_service: LatexService, notion_service: NotionService) -> None:
        self.openai_client = openai_client
        self.latex_service = latex_service
        self.notion_service = notion_service

    def tailor_resume(
        self,
        job_metadata: dict[str, Any],
        master_resume_tex_content: str,
        notion_page_id: str,
    ) -> None:
        """
        Tailor the resume for a job, save/compile files, and output to 'outputs' folder.
        """

        settings = get_settings()

        # 1. Load and format prompts
        prompts_dir = Path(settings.PROMPTS_DIRECTORY)

        # Load system prompt
        system_prompt_path = prompts_dir / settings.TAILOR_RESUME_SYSTEM_PROMPT_FILENAME
        system_prompt = system_prompt_path.read_text(encoding="utf-8")

        # Load and format user prompt
        user_prompt_path = prompts_dir / settings.TAILOR_RESUME_USER_PROMPT_FILENAME
        user_prompt_template = user_prompt_path.read_text(encoding="utf-8")

        # Load tailoring rules from file
        tailoring_rules_path = prompts_dir / settings.TAILORING_RULES_FILENAME
        tailoring_rules = tailoring_rules_path.read_text(encoding="utf-8")
        user_prompt = user_prompt_template.format(
            job_metadata_block=json.dumps(job_metadata, indent=2),
            tailoring_rules=tailoring_rules,
            tex_master_resume=master_resume_tex_content,
        )

        # Determine output directory
        base_output_dir = settings.BASE_OUTPUT_DIR
        if settings.DEV_MODE:
            target_output_dir = base_output_dir
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_page_id = str(notion_page_id).replace("-", "")
            target_output_dir = base_output_dir / "runs" / f"{timestamp}_{safe_page_id}"
        target_output_dir.mkdir(parents=True, exist_ok=True)

        # Initial Diff Application and Compilation Loop
        max_diff_retries = settings.DIFF_MAX_RETRIES
        tailored_tex_content = master_resume_tex_content  # Start with master content
        final_tailored_tex_path = None
        compiled_tailored_pdf_path = None

        for attempt in range(1, max_diff_retries + 1):
            # logger.info(f"Initial tailoring attempt {attempt}/{max_diff_retries}")
            llm_response = self.openai_client.get_response(
                system_prompt, user_prompt, model_name=settings.DEFAULT_MODEL_NAME
            )
            try:
                current_tex_to_diff_against = (
                    master_resume_tex_content  # Always diff against original master for initial tailoring
                )
                tailored_tex_content = apply_diff(current_tex_to_diff_against, llm_response)

                final_tailored_tex_path = self.latex_service.save_tex_file(
                    content=tailored_tex_content,
                    filename_stem=settings.TAILORED_RESUME_STEM,
                    target_directory=target_output_dir,
                )
                compiled_tailored_pdf_path = self.latex_service.compile_resume(final_tailored_tex_path)
                logger.info(f"Initial tailoring attempt {attempt} successful.")
                break  # Successful initial tailoring and compilation
            except ValueError as e:
                logger.warning(f"Initial tailoring attempt {attempt} failed: {e}")
                if attempt == max_diff_retries:
                    logger.error(f"Failed to apply initial diff after {max_diff_retries} attempts.")
                    raise ValueError(f"Failed to apply initial diff after {max_diff_retries} attempts: {e}")
                continue  # Retry initial tailoring
        else:
            # This else block executes if the loop completes without a break (all retries failed)
            logger.error("All initial tailoring attempts failed.")
            # Ensure compiled_tailored_pdf_path remains None or indicates failure
            compiled_tailored_pdf_path = None  # Explicitly set to None

        # PDF Length Reduction (if needed)
        if compiled_tailored_pdf_path and compiled_tailored_pdf_path.exists():
            try:
                page_count = self.latex_service.get_pdf_page_count(compiled_tailored_pdf_path)
                logger.info(f"Initial tailored PDF has {page_count} pages.")

                if page_count > 1:
                    # `tailored_tex_content` and `compiled_tailored_pdf_path` will be updated by the helper method.
                    tailored_tex_content, compiled_tailored_pdf_path = self._reduce_pdf_to_one_page(
                        current_tex_content=tailored_tex_content,
                        current_pdf_path=compiled_tailored_pdf_path,
                        initial_page_count=page_count,
                        target_output_dir=target_output_dir,
                    )
            except RuntimeError as e_pdf_processing:  # Covers errors from get_pdf_page_count or _reduce_pdf_to_one_page
                logger.critical(
                    f"Critical error during PDF processing or reduction: {e_pdf_processing}. Subsequent steps might be affected or fail."
                )
                # Depending on the severity or desired behavior, you might want to re-raise e_pdf_processing
                # or ensure compiled_tailored_pdf_path is None to prevent further operations like Notion upload.
                # For now, if _reduce_pdf_to_one_page raises, compiled_tailored_pdf_path might not be updated to a 1-page PDF.
                # The existing check below for PDF existence will handle if it became None or points to an invalid path.
            except FileNotFoundError:  # From the initial get_pdf_page_count
                logger.error("Initial compiled PDF not found. Skipping length reduction.")

        # Ensure final_tailored_tex_path and compiled_tailored_pdf_path are valid before proceeding
        # If initial compilation failed, compiled_tailored_pdf_path will be None or non-existent
        if not (
            final_tailored_tex_path
            and final_tailored_tex_path.exists()
            and compiled_tailored_pdf_path
            and compiled_tailored_pdf_path.exists()
        ):
            logger.error("Tailored PDF could not be generated. Aborting Notion upload and diff generation.")
            # Consider raising an error here or ensuring subsequent steps handle this gracefully
            return  # Exit if no PDF was successfully generated

        # 7. Remove all files from the resume property before uploading new file
        self.notion_service.update_page_property(
            page_id=notion_page_id,
            property_name=settings.TAILORED_RESUME_PROPERTY_NAME,
            property_value={"files": []},
        )

        # 8. Reset resume property and upload tailored PDF to Notion
        if compiled_tailored_pdf_path and compiled_tailored_pdf_path.exists():
            self.notion_service.upload_file_to_page_property(
                file_path=compiled_tailored_pdf_path,
                page_id=notion_page_id,
                property_name=settings.TAILORED_RESUME_PROPERTY_NAME,
            )
        else:
            # Log an error or handle if PDF compilation failed
            # logger.error(f"Failed to compile tailored PDF for {final_tailored_tex_path}")
            pass

        # 9. Generate diff .tex and .pdf, then upload diff PDF to Notion
        master_resume_path = Path(settings.MASTER_RESUME_PATH)

        diff_tex_result_path = self.latex_service.run_latexdiff(
            original_tex_path=master_resume_path,
            tailored_tex_path=final_tailored_tex_path,
            diff_output_stem=settings.TAILORED_RESUME_DIFF_STEM,  # e.g., "tailored_resume_diff"
            target_directory=target_output_dir,
        )

        if diff_tex_result_path and diff_tex_result_path.exists():
            # Compile diff .tex to .pdf (saved in the same directory as the diff .tex file)
            compiled_diff_pdf_path = self.latex_service.compile_resume(diff_tex_result_path)

            if compiled_diff_pdf_path and compiled_diff_pdf_path.exists():
                self.notion_service.upload_file_to_page_property(
                    file_path=compiled_diff_pdf_path,
                    page_id=notion_page_id,
                    property_name=settings.TAILORED_RESUME_PROPERTY_NAME,
                )
            else:
                # Log an error or handle if diff PDF compilation failed
                # logger.error(f"Failed to compile diff PDF for {diff_tex_result_path}")
                pass

    def _reduce_pdf_to_one_page(
        self,
        current_tex_content: str,
        current_pdf_path: Path,
        initial_page_count: int,
        target_output_dir: Path,
    ) -> tuple[str, Path]:
        settings = get_settings()
        logger.info(f"Resume is {initial_page_count} pages. Attempting to reduce to 1 page.")

        loop_tex_content = current_tex_content
        loop_pdf_path = current_pdf_path
        loop_page_count = initial_page_count

        for reduction_attempt in range(1, settings.PDF_REDUCTION_MAX_RETRIES + 1):
            logger.info(f"PDF reduction attempt {reduction_attempt}/{settings.PDF_REDUCTION_MAX_RETRIES}")

            try:
                overflow_page_text = self.latex_service.get_text_from_pdf_page(loop_pdf_path, 2)
                if not overflow_page_text:
                    raise RuntimeError("Extracted overflow text was empty.")
            except (RuntimeError, FileNotFoundError) as e:
                err_msg = f"Critical: Could not get overflow text from page 2 of {loop_pdf_path}. Reason: {e}. Terminating reduction."
                logger.critical(err_msg)
                raise RuntimeError(err_msg) from e

            # Build reduction prompt from template instead of hardcoding
            prompts_dir = Path(settings.PROMPTS_DIRECTORY)
            reduction_prompt_path = prompts_dir / settings.PDF_REDUCTION_PROMPT_FILENAME
            reduction_prompt_template = reduction_prompt_path.read_text(encoding="utf-8")

            # Fill in template placeholders
            reduction_user_prompt = reduction_prompt_template.format(
                page_count=str(loop_page_count),
                overflow_page_text=overflow_page_text,
                current_tex_content=loop_tex_content,
            )

            # We call get_response with only the user_prompt. The client will handle the history.
            reduction_llm_response = self.openai_client.get_response(
                sys_prompt=None,  # System prompt is already in the history
                user_prompt=reduction_user_prompt,
                model_name=settings.DEFAULT_MODEL_NAME,
            )

            try:
                loop_tex_content = apply_diff(loop_tex_content, reduction_llm_response)
                loop_pdf_path = self.latex_service.save_tex_file(
                    content=loop_tex_content,
                    filename_stem=settings.TAILORED_RESUME_STEM,
                    target_directory=target_output_dir,
                )
                loop_pdf_path = self.latex_service.compile_resume(loop_pdf_path)
                loop_page_count = self.latex_service.get_pdf_page_count(loop_pdf_path)
                logger.info(f"After reduction attempt {reduction_attempt}, PDF has {loop_page_count} pages.")

                if loop_page_count <= 1:
                    logger.info("Successfully reduced PDF to 1 page.")
                    break

            except ValueError as e_reduce_diff:
                logger.warning(f"Failed to apply reduction diff on attempt {reduction_attempt}: {e_reduce_diff}")
                if reduction_attempt == settings.PDF_REDUCTION_MAX_RETRIES:
                    logger.warning("Max reduction retries reached. Proceeding with current PDF version.")
                    break
                continue

        if loop_page_count > 1:
            logger.warning(
                f"Failed to reduce PDF to 1 page after {settings.PDF_REDUCTION_MAX_RETRIES} attempts. "
                f"Final page count: {loop_page_count}"
            )

        return loop_tex_content, loop_pdf_path
