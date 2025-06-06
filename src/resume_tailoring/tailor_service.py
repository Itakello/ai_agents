import datetime
import json
import re
from pathlib import Path
from typing import Any

from src.common.llm_clients import OpenAIClient
from src.common.notion_service import NotionService
from src.core.config import get_settings

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
        occ = src.find(search)
        if occ == -1:
            raise ValueError(f"Search block not found:\n{search[:80]}…")
        return src.replace(search, replace, 1)

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

        # Format user prompt with actual data
        tailoring_rules = getattr(settings, "TAILORING_RULES", "No specific tailoring rules provided")
        user_prompt = user_prompt_template.format(
            job_metadata_block=json.dumps(job_metadata, indent=2),
            tailoring_rules=tailoring_rules,
            tex_master_resume=master_resume_tex_content,
        )

        # 2. Determine output directory and prepare for diff/apply/compile with retry logic
        base_output_dir = settings.BASE_OUTPUT_DIR
        if settings.DEV_MODE:
            target_output_dir = base_output_dir
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_page_id = str(notion_page_id).replace("-", "")
            target_output_dir = base_output_dir / "runs" / f"{timestamp}_{safe_page_id}"

        target_output_dir.mkdir(parents=True, exist_ok=True)

        max_retries = settings.DIFF_MAX_RETRIES
        for attempt in range(1, max_retries + 1):
            llm_response = self.openai_client.get_response(
                system_prompt, user_prompt, model_name=settings.DEFAULT_MODEL_NAME
            )
            try:
                tailored_tex_content = apply_diff(master_resume_tex_content, llm_response)
                # Save tailored resume .tex file and compile PDF within retry loop
                final_tailored_tex_path = self.latex_service.save_tex_file(
                    content=tailored_tex_content,
                    filename_stem=settings.TAILORED_RESUME_STEM,
                    target_directory=target_output_dir,
                )
                compiled_tailored_pdf_path = self.latex_service.compile_resume(final_tailored_tex_path)
                break
            except ValueError as e:
                if attempt == max_retries:
                    raise ValueError(f"Failed to apply diff after {max_retries} attempts: {e}")
                continue

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
