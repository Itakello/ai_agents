import subprocess
from pathlib import Path
from shutil import copy2

from src.common.utils import write_file_content
from src.core.config import Settings
from src.core.logger import logger
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
        """
        Compile a .tex file to PDF using a temporary latex_build/ directory for all pdflatex outputs.
        Only the PDF is copied to the tex_file_path's parent directory; auxiliary files remain in latex_build/.
        """

        # Use latex_build/ in the codebase for aux files
        build_dir = tex_file_path.parent / "latex_build"
        build_dir.mkdir(exist_ok=True)
        pdf_path = self.pdf_compiler.compile_tex_to_pdf(tex_file_path, build_dir)

        # Move only the PDF to the output dir (where the .tex file is)
        output_pdf = tex_file_path.parent / pdf_path.name
        copy2(pdf_path, output_pdf)
        return output_pdf

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

    def get_pdf_page_count(self, pdf_path: Path) -> int:
        """Get the number of pages in a PDF file using pdfinfo."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            # Ensure pdfinfo is available, consider adding a check or specific error handling
            cmd = ["pdfinfo", str(pdf_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
            for line in result.stdout.splitlines():
                if line.lower().startswith("pages:"):
                    return int(line.split(":")[1].strip())
            raise ValueError("Could not find page count in pdfinfo output.")
        except FileNotFoundError:
            # This specific exception is for when 'pdfinfo' itself is not found
            # logger.error("pdfinfo command not found. Please ensure it's installed and in your PATH.")
            raise RuntimeError("pdfinfo command not found. Please ensure it's installed and in your PATH.")
        except (subprocess.CalledProcessError, ValueError) as e:
            # This handles errors from pdfinfo execution or if 'Pages:' line is missing
            # logger.error(f"Error getting PDF page count for {pdf_path}: {e}")
            raise RuntimeError(f"Error getting PDF page count for {pdf_path}: {e}")

    def get_text_from_pdf_page(self, pdf_path: Path, page_number: int) -> str | None:
        """Extract text from a specific page of a PDF file using pdftotext."""
        if not pdf_path.exists():
            logger.error(f"PDF file not found for text extraction: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            # pdftotext outputs to stdout by default if '-' is used for the output file
            cmd = [
                "pdftotext",
                "-f",
                str(page_number),  # First page to convert
                "-l",
                str(page_number),  # Last page to convert
                str(pdf_path),
                "-",  # Output to stdout
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
            return result.stdout
        except FileNotFoundError:
            # This specific exception is for when 'pdftotext' itself is not found
            logger.error("pdftotext command not found. Please ensure it's installed and in your PATH.")
            raise RuntimeError("pdftotext command not found. Please ensure it's installed and in your PATH.")
        except subprocess.CalledProcessError as e:
            # This handles errors from pdftotext execution (e.g., invalid page, corrupted PDF)
            logger.error(
                f"Error extracting text from PDF page {page_number} of {pdf_path} using pdftotext: {e}. Stderr: {e.stderr}"
            )
            # Return None to indicate failure to extract text from that specific page, allowing the process to continue if desired.
            return None
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error extracting text from PDF {pdf_path} on page {page_number}: {e}")
            raise RuntimeError(f"Unexpected error extracting text from PDF {pdf_path} on page {page_number}: {e}")
