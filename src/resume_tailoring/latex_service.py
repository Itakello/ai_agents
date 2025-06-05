import subprocess
from pathlib import Path

from src.common.utils import write_file_content
from src.core.config import Settings
from src.resume_tailoring.pdf_compiler import PDFCompiler


class LatexService:
    def __init__(self, pdf_compiler: PDFCompiler, settings: Settings) -> None:
        self.pdf_compiler = pdf_compiler
        self.settings = settings

    def save_tex_file(
        self,
        content: str,
        filename_stem: str,
        target_directory: Path,
    ) -> Path:
        target_directory.mkdir(parents=True, exist_ok=True)
        tex_path = target_directory / f"{filename_stem}.tex"
        write_file_content(tex_path, content)
        return tex_path

    def compile_resume(self, tex_file_path: Path) -> Path:
        output_dir = tex_file_path.parent
        return self.pdf_compiler.compile_tex_to_pdf(tex_file_path, output_dir)

    def run_latexdiff(
        self,
        original_tex_path: Path,
        tailored_tex_path: Path,
        diff_output_stem: str,
        target_directory: Path,
    ) -> Path | None:
        target_directory.mkdir(parents=True, exist_ok=True)
        diff_tex_path = target_directory / f"{diff_output_stem}.tex"
        cmd = [
            self.settings.LATEXDIFF_COMMAND,
            "--type=WORD",
            "-t",
            "UNDERLINE",
            "--append-textcmd=introduction",
            "--append-textcmd=resumeItem",
            "--append-textcmd=resumeItemListStart",
            "--append-textcmd=resumeItemListEnd",
            "--append-textcmd=resumeSubheading",
            "--append-textcmd=resumeSubHeadingListStart",
            "--append-textcmd=resumeSubHeadingListEnd",
            "--append-textcmd=techSkillsItem",
            str(original_tex_path),
            str(tailored_tex_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            write_file_content(diff_tex_path, result.stdout)
            return diff_tex_path
        except Exception:
            return None
