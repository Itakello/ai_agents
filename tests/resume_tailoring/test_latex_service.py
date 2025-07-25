import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import the module under test
from src.core.config import Settings
from src.resume_tailoring.latex_service import LatexService


class DummyPDFCompiler:
    def compile_tex_to_pdf(self, tex_file_path: Path, output_directory: Path) -> Path | None:
        return output_directory / (tex_file_path.stem + ".pdf")


def make_settings(tmp_path: Path) -> Settings:
    class TestSettings(Settings):
        DEFAULT_OUTPUT_DIR: Path = tmp_path
        LATEXDIFF_COMMAND: str = "latexdiff"

    return TestSettings(
        OPENAI_API_KEY="test_openai_key_123",
        NOTION_API_KEY="test_notion_key_123",
        NOTION_DATABASE_ID="test_db_id",
        MASTER_RESUME_PATH=tmp_path / "master.tex",
    )


def test_save_tex_file(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        filename = "resume1.tex"
        file_path = tmp_path / filename

        service = LatexService(DummyPDFCompiler(), settings)  # type: ignore[arg-type]
        content = "\\documentclass{article}\\begin{document}Test\\end{document}"
        tex_path = service.save_tex_file(content, file_path.stem, file_path)
        assert tex_path.exists()
        assert tex_path.read_text() == content
        assert tex_path.name == filename


def test_compile_resume(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = LatexService(DummyPDFCompiler(), settings)  # type: ignore[arg-type]
    tex_path = tmp_path / "resume2.tex"
    tex_path.write_text("\\documentclass{article}\\begin{document}Test\\end{document}")
    # Create the dummy PDF file at the expected output location
    build_dir = tmp_path / "latex_build"
    build_dir.mkdir(exist_ok=True)
    dummy_pdf_path = build_dir / "resume2.pdf"
    dummy_pdf_path.write_bytes(b"%PDF-1.4 dummy content")
    pdf_path = service.compile_resume(tex_path)
    assert pdf_path == tex_path.parent / "resume2.pdf"


def test_run_latexdiff_success(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = LatexService(DummyPDFCompiler(), settings)  # type: ignore[arg-type]
    orig = tmp_path / "orig.tex"
    tailored = tmp_path / "tailored.tex"
    output_dir = tmp_path / "output"
    orig.write_text("A")
    tailored.write_text("B")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="DIFF_CONTENT", returncode=0)
        diff_path = service.run_latexdiff(orig, tailored, "diff1", output_dir)
        assert diff_path is not None
        assert diff_path.exists()
        assert diff_path.read_text() == "DIFF_CONTENT"
        assert (output_dir / "diff1.tex") == diff_path


def test_run_latexdiff_failure(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = LatexService(DummyPDFCompiler(), settings)  # type: ignore[arg-type]
    orig = tmp_path / "orig.tex"
    tailored = tmp_path / "tailored.tex"
    output_dir = tmp_path / "output"
    orig.write_text("A")
    tailored.write_text("B")
    with patch("subprocess.run", side_effect=Exception("fail")):
        diff_path = service.run_latexdiff(orig, tailored, "diff2", output_dir)
        assert diff_path is None
