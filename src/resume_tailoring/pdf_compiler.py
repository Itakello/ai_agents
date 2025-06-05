import subprocess
from collections.abc import Sequence
from pathlib import Path

from src.core.logger import logger


class PDFCompilationError(Exception):
    """Raised when PDF compilation from LaTeX fails."""

    pass


class PDFCompiler:
    def __init__(
        self,
        pdflatex_cmd: str = "pdflatex",
        pdflatex_args: Sequence[str] | None = None,
        command_template: str | None = None,
    ) -> None:
        """
        Args:
            pdflatex_cmd: The pdflatex executable (default: "pdflatex").
            pdflatex_args: List of default arguments for pdflatex.
            command_template: Optional shell command template (overrides cmd/args if set).
        """
        self.pdflatex_cmd = pdflatex_cmd
        self.pdflatex_args = pdflatex_args or [
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory=%OUTDIR%",
            "%DOC%",
        ]
        self.command_template = command_template

    def compile_tex_to_pdf(self, tex_file_path: Path, output_directory: Path) -> Path:
        """
        Compiles a .tex file to PDF using pdflatex.
        Args:
            tex_file_path: Path to the .tex file.
            output_directory: Directory to place the output PDF.
        Returns:
            Path to the generated PDF.
        """
        output_directory.mkdir(parents=True, exist_ok=True)
        tex_file_path = tex_file_path.resolve()
        output_directory = output_directory.resolve()
        pdf_path = output_directory / (tex_file_path.stem + ".pdf")

        # Prepare command
        if self.command_template:
            cmd_str: str = self.command_template.replace("%OUTDIR%", str(output_directory)).replace(
                "%DOC%", str(tex_file_path)
            )
            cmd_to_run: str | list[str] = cmd_str
            shell = True
        else:
            args = [
                arg.replace("%OUTDIR%", str(output_directory)).replace("%DOC%", str(tex_file_path))
                for arg in self.pdflatex_args
            ]
            cmd_to_run = [self.pdflatex_cmd] + args
            shell = False

        last_stdout = ""
        last_stderr = ""

        for i in range(2):  # Run up to 2 times for cross-referencing
            current_cmd_to_run = cmd_to_run
            if shell and isinstance(current_cmd_to_run, list):  # Ensure command is a string if shell=True
                current_cmd_to_run = " ".join(current_cmd_to_run)

            logger.info(
                f"Running pdflatex (attempt {i + 1}/2): {' '.join(current_cmd_to_run) if isinstance(current_cmd_to_run, list) else current_cmd_to_run}"
            )
            result = subprocess.run(
                current_cmd_to_run,
                shell=shell,
                capture_output=True,
                text=True,  # Decode stdout/stderr as text
                cwd=tex_file_path.parent,
            )

            last_stdout = result.stdout
            last_stderr = result.stderr

            if result.returncode != 0:
                error_message = (
                    f"Failed to compile {tex_file_path} to PDF on attempt {i + 1}.\n"
                    f"Return code: {result.returncode}\n"
                    f"Working directory: {tex_file_path.parent}\n"
                    f"Command: {' '.join(current_cmd_to_run) if isinstance(current_cmd_to_run, list) else current_cmd_to_run}\n"
                    f"STDOUT:\n{result.stdout}\n"
                    f"STDERR:\n{result.stderr}"
                )
                logger.error(error_message)
                raise PDFCompilationError(error_message)

        if pdf_path.exists():
            logger.info(f"Successfully compiled {tex_file_path} to {pdf_path}")
            return pdf_path

        # This case should ideally be caught by the returncode check, but as a fallback:
        fallback_error_message = (
            f"Failed to compile {tex_file_path} to PDF. PDF not found after 2 attempts.\n"
            f"Working directory: {tex_file_path.parent}\n"
            f"Command: {' '.join(cmd_to_run) if isinstance(cmd_to_run, list) else cmd_to_run}\n"
            f"Last STDOUT:\n{last_stdout}\n"
            f"Last STDERR:\n{last_stderr}"
        )
        logger.error(fallback_error_message)
        raise PDFCompilationError(fallback_error_message)
