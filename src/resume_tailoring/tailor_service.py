import json
import re
from pathlib import Path
from typing import Any

from src.resume_tailoring.models import TailoredResumeOutput

from ..common.llm_clients import OpenAIClient
from ..common.notion_service import NotionService
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
        # 1. Load and format prompts
        prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        # Load system prompt
        system_prompt_path = prompts_dir / "tailor_resume_llm_prompt.txt"
        system_prompt = system_prompt_path.read_text(encoding="utf-8")

        # Load and format user prompt
        user_prompt_path = prompts_dir / "tailor_resume_llm_user_prompt.txt"
        user_prompt_template = user_prompt_path.read_text(encoding="utf-8")

        # Format user prompt with actual data
        user_prompt = user_prompt_template.format(
            job_metadata_block=json.dumps(job_metadata, indent=2),
            tailoring_rules="No specific tailoring rules provided",  # You can make this configurable
            tex_master_resume=master_resume_tex_content,
        )

        # 2. Call OpenAIClient with system and user prompts to get diff blocks
        llm_response = self.openai_client.get_response(system_prompt, user_prompt, model_name="gpt-4.1")

        # 3. Apply diff using the new apply_diff function
        tailored_tex_content = apply_diff(master_resume_tex_content, llm_response)

        # 4. Create output object
        output = TailoredResumeOutput(
            tailored_tex_content=tailored_tex_content, changes_summary="Resume tailored using diff-based approach"
        )

        # 5. Create outputs directory
        outputs_dir = Path(__file__).parent.parent.parent / "outputs"
        outputs_dir.mkdir(exist_ok=True)

        # 6. Save tailored tex file to outputs directory
        tailored_tex_path = outputs_dir / "tailored_resume.tex"
        tailored_tex_path.write_text(output.tailored_tex_content, encoding="utf-8")

        # 7. Compile tailored tex to PDF (using latex_service but save to outputs)
        tailored_pdf_path = self.latex_service.compile_resume(tailored_tex_path)

        # 8. Upload tailored PDF to Notion
        from src.core.config import get_settings

        settings = get_settings()
        if tailored_pdf_path:
            self.notion_service.upload_file_to_page_property(
                outputs_dir / (settings.TAILORED_RESUME_STEM + ".pdf"),
                notion_page_id,
                settings.TAILORED_RESUME_PROPERTY_NAME,
            )

        # 9. Generate diff and upload diff PDF
        if tailored_pdf_path:
            from src.core.config import get_settings

            settings = get_settings()
            master_resume_path = Path(settings.MASTER_RESUME_PATH)
            diff_tex_path = self.latex_service.run_latexdiff(
                master_resume_path, tailored_tex_path, settings.TAILORED_RESUME_DIFF_STEM, output_subdir="outputs"
            )
            if diff_tex_path:
                diff_pdf_path = self.latex_service.compile_resume(diff_tex_path)
                if diff_pdf_path:
                    self.notion_service.upload_file_to_page_property(
                        outputs_dir / (settings.TAILORED_RESUME_DIFF_STEM + ".pdf"),
                        notion_page_id,
                        settings.TAILORED_RESUME_DIFF_PROPERTY_NAME,
                    )
