"""End-to-end tests for the Job Finder Assistant application."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.main import main


class TestEndToEnd:
    @pytest.fixture
    def mock_settings(self, tmp_path: Path) -> MagicMock:
        """Create mock settings with test values."""
        settings = MagicMock(spec=Settings)
        settings.OPENAI_API_KEY = "test-openai-key"
        settings.NOTION_API_KEY = "test-notion-key"
        settings.NOTION_DATABASE_ID = "test-db-id"
        settings.MASTER_RESUME_PATH = tmp_path / "master_resume.tex"
        settings.DEFAULT_MODEL_NAME = "gpt-4"
        settings.LOG_LEVEL = "INFO"
        return settings

    @pytest.fixture
    def mock_job_metadata(self) -> dict:
        """Sample job metadata for testing."""
        return {
            "id": "test-page-id",
            "title": "Software Engineer",
            "company": "Test Company",
            "location": "Remote",
            "description": "Test job description",
            "requirements": ["Python", "Testing"],
            "url": "https://example.com/job/123",
        }

    def test_extract_command_end_to_end(self, mock_settings: MagicMock, mock_job_metadata: dict) -> None:
        """Test the complete extract command workflow."""
        with (
            patch("src.main.Settings", return_value=mock_settings),
            patch("src.main.parse_arguments") as mock_parse_args,
            patch("src.main.NotionSyncService") as mock_notion,
            patch("src.main.ExtractorService") as mock_extractor,
        ):
            # Setup mock arguments
            mock_parse_args.return_value = MagicMock(
                command="extract", job_url="https://example.com/job/123", model="gpt-4", add_properties_options=False
            )

            # Setup mock services
            mock_notion_instance = mock_notion.return_value
            mock_notion_instance.get_database_schema.return_value = {
                "properties": {
                    "title": {"type": "title"},
                    "company": {"type": "rich_text"},
                    "location": {"type": "rich_text"},
                    "description": {"type": "rich_text"},
                    "requirements": {"type": "multi_select"},
                    "url": {"type": "url"},
                }
            }
            mock_notion_instance.save_or_update_extracted_data = AsyncMock()
            mock_notion_instance.find_page_by_url = AsyncMock()
            mock_notion_instance.find_page_by_url.return_value = mock_job_metadata

            mock_extractor_instance = mock_extractor.return_value
            mock_extractor_instance.extract_metadata_from_job_url.return_value = mock_job_metadata

            # Execute main function
            main()

            # Verify the complete workflow
            mock_notion_instance.get_database_schema.assert_called_once()
            mock_extractor_instance.extract_metadata_from_job_url.assert_called_once_with(
                "https://example.com/job/123", mock_notion_instance.get_database_schema.return_value, "gpt-4"
            )
            mock_notion_instance.save_or_update_extracted_data.assert_called_once()

    def test_tailor_resume_command_end_to_end(
        self, mock_settings: MagicMock, mock_job_metadata: dict, tmp_path: Path
    ) -> None:
        """Test the complete tailor-resume command workflow."""
        # Create a test master resume file
        master_resume = tmp_path / "master_resume.tex"
        master_resume.write_text(r"""
        \documentclass{article}
        \begin{document}
        Test Resume Content
        \end{document}
        """)

        with (
            patch("src.main.Settings", return_value=mock_settings),
            patch("src.main.parse_arguments") as mock_parse_args,
            patch("src.main.NotionSyncService") as mock_notion,
            patch("src.main.TailorService") as mock_tailor,
        ):
            # Setup mock arguments
            mock_parse_args.return_value = MagicMock(command="tailor-resume", job_url="https://example.com/job/123")

            # Setup mock services
            mock_notion_instance = mock_notion.return_value
            mock_notion_instance.find_page_by_url = AsyncMock()
            mock_notion_instance.find_page_by_url.return_value = mock_job_metadata

            mock_tailor_instance = mock_tailor.return_value

            # Execute main function
            main()

            # Verify the complete workflow
            mock_notion_instance.find_page_by_url.assert_called_once_with("https://example.com/job/123")
            mock_tailor_instance.tailor_resume.assert_called_once_with(
                job_metadata=mock_job_metadata,
                master_resume_tex_content=master_resume.read_text(),
                notion_page_id=mock_job_metadata["id"],
            )
