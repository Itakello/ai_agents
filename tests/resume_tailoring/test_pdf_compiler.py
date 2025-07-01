from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.resume_tailoring.pdf_compiler import PDFCompilationError, PDFCompiler


@pytest.fixture
def minimal_tex_file(tmp_path: Path) -> Path:
    tex_content = r"""
    \documentclass{article}
    \begin{document}
    Hello, world!
    \end{document}
    """
    tex_file = tmp_path / "test_resume.tex"
    tex_file.write_text(tex_content)
    return tex_file


def test_compile_tex_to_pdf_success(monkeypatch: pytest.MonkeyPatch, minimal_tex_file: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    pdf_path = output_dir / "test_resume.pdf"

    def fake_run(cmd: str | list[str], shell: bool, capture_output: bool, cwd: str, **kwargs: object) -> MagicMock:
        # Simulate pdflatex success by creating the PDF file
        output_dir.mkdir(exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")
        mock_result = MagicMock()
        mock_result.returncode = 0
        return mock_result

    with patch("subprocess.run", side_effect=fake_run) as mock_run:
        compiler = PDFCompiler()
        result = compiler.compile_tex_to_pdf(minimal_tex_file, output_dir)
        assert result == pdf_path
        assert pdf_path.exists()
        assert mock_run.call_count == 2  # Should run twice
        # Check that the command includes the correct output directory and tex file
        called_args = mock_run.call_args[0][0]
        assert str(output_dir) in str(called_args)
        assert str(minimal_tex_file) in str(called_args)


def test_compile_tex_to_pdf_failure(monkeypatch: pytest.MonkeyPatch, minimal_tex_file: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"

    def fake_run(cmd: str, shell: bool, capture_output: bool, cwd: str, **kwargs: object) -> MagicMock:
        mock_result = MagicMock()
        mock_result.returncode = 1
        return mock_result

    with patch("subprocess.run", side_effect=fake_run):
        compiler = PDFCompiler()
        with pytest.raises(PDFCompilationError):
            compiler.compile_tex_to_pdf(minimal_tex_file, output_dir)
        assert not (output_dir / "test_resume.pdf").exists()


def test_compile_tex_to_pdf_with_command_template(
    monkeypatch: pytest.MonkeyPatch, minimal_tex_file: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    pdf_path = output_dir / "test_resume.pdf"

    def fake_run(cmd: str | list[str], shell: bool, capture_output: bool, cwd: str, **kwargs: object) -> MagicMock:
        output_dir.mkdir(exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")
        mock_result = MagicMock()
        mock_result.returncode = 0
        return mock_result

    with patch("subprocess.run", side_effect=fake_run) as mock_run:
        template = "pdflatex -output-directory=%OUTDIR% %DOC%"
        compiler = PDFCompiler(command_template=template)
        result = compiler.compile_tex_to_pdf(minimal_tex_file, output_dir)
        assert result == pdf_path
        assert pdf_path.exists()
        assert mock_run.call_count == 2
        called_cmd = mock_run.call_args[0][0]
        # called_cmd is a string, so just check substring
        assert str(output_dir) in str(called_cmd)
        assert str(minimal_tex_file) in str(called_cmd)
