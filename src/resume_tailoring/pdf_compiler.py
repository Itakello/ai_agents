import subprocess
from collections.abc import Sequence
from pathlib import Path


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
            cmd: str | list[str] = self.command_template.replace("%OUTDIR%", str(output_directory)).replace(
                "%DOC%", str(tex_file_path)
            )
            shell = True
        else:
            args = [
                arg.replace("%OUTDIR%", str(output_directory)).replace("%DOC%", str(tex_file_path))
                for arg in self.pdflatex_args
            ]
            cmd = [self.pdflatex_cmd] + args
            shell = False
        for _ in range(2):
            cmd_to_run = cmd
            if shell and isinstance(cmd, list):
                cmd_to_run = " ".join(cmd)
            result = subprocess.run(cmd_to_run, shell=shell, capture_output=True, cwd=tex_file_path.parent)
            if result.returncode != 0:
                break
        if pdf_path.exists():
            return pdf_path
        raise PDFCompilationError(f"Failed to compile {tex_file_path} to PDF")
