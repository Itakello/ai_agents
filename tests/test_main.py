"""Tests for the main application functionality."""

from unittest.mock import MagicMock, patch

import pytest

from src.main import display_results, main, parse_arguments

DUMMY_SETTINGS = dict(
    OPENAI_API_KEY="sk-test",
    NOTION_API_KEY="secret-test",
    NOTION_DATABASE_ID="test-db",
    MASTER_RESUME_PATH="/tmp/test_resume.tex",
)


class TestParseArguments:
    """Test the parse_arguments function."""

    @patch("sys.argv", ["main.py", "extract", "https://example.com/job"])
    def test_parse_arguments_with_defaults(self) -> None:
        """Test parsing arguments with default model."""
        args = parse_arguments(default_model="gpt-4-test")
        assert args.command == "extract"
        assert args.job_url == "https://example.com/job"
        assert args.model == "gpt-4-test"

    @patch("sys.argv", ["main.py", "extract", "https://example.com/job", "--model", "gpt-3.5-turbo"])
    def test_parse_arguments_with_custom_model(self) -> None:
        """Test parsing arguments with custom model."""
        args = parse_arguments(default_model="gpt-4-test")
        assert args.command == "extract"
        assert args.job_url == "https://example.com/job"
        assert args.model == "gpt-3.5-turbo"

    # The CLI does not support --method, so this test is removed.

    @patch("sys.argv", ["main.py"])
    def test_parse_arguments_missing_url(self) -> None:
        """Test parsing arguments when no command is specified."""
        with pytest.raises(SystemExit):
            parse_arguments(default_model="gpt-4-test")


class TestMain:
    """Test the main function of the Job Finder Assistant."""

    @patch("src.main.ExtractorService")
    @patch("src.main.NotionService")
    @patch("src.main.OpenAIClient")
    @patch("src.main.Settings")
    @patch("src.main.convert_openai_response_to_notion_update")
    @patch("src.main.display_results")
    @patch("src.main.parse_arguments")
    def test_main_successful_execution(
        self,
        mock_parse_arguments: MagicMock,
        mock_display_results: MagicMock,
        mock_convert: MagicMock,
        mock_settings: MagicMock,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        mock_extractor_service: MagicMock,
    ) -> None:
        """Test successful execution of the main function."""
        # Setup argument mock
        mock_args = MagicMock()
        mock_args.command = "extract"
        mock_args.job_url = "https://example.com/job"
        mock_args.model = "gpt-4o"
        mock_args.method = "openai_web_search"
        mock_args.add_properties_options = False
        mock_parse_arguments.return_value = mock_args

        # Setup settings mock
        mock_settings_instance = MagicMock()
        mock_settings_instance.OPENAI_API_KEY = "test-openai-key"
        mock_settings_instance.NOTION_API_KEY = "test-notion-key"
        mock_settings_instance.NOTION_DATABASE_ID = "test-db-id"
        mock_settings_instance.LOG_LEVEL = "INFO"
        mock_settings.return_value = mock_settings_instance

        mock_notion_service_instance = MagicMock()
        mock_database_schema = {
            "job_title": {"type": "title"},
            "company": {"type": "rich_text"},
            "salary": {"type": "number"},
        }
        mock_notion_service_instance.get_database_schema.return_value = mock_database_schema
        mock_notion_service.return_value = mock_notion_service_instance

        mock_extractor_service_instance = MagicMock()
        mock_extracted_metadata = {
            "job_title": "Software Engineer",
            "company": "Tech Corp",
            "salary": 100000,
        }
        mock_extractor_service_instance.extract_metadata_from_job_url.return_value = mock_extracted_metadata
        mock_extractor_service.return_value = mock_extractor_service_instance

        mock_notion_update = {
            "properties": {
                "job_title": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
                "company": {"rich_text": [{"text": {"content": "Tech Corp"}}]},
                "salary": {"number": 100000.0},
            }
        }
        mock_convert.return_value = mock_notion_update

        # Execute main function
        main()

        # Verify all components were called correctly
        mock_settings.assert_called_once()
        mock_openai_client.assert_called_once_with(api_key="test-openai-key")
        mock_notion_service.assert_called_once_with(api_key="test-notion-key", database_id="test-db-id")
        mock_extractor_service.assert_called_once()

        mock_notion_service_instance.get_database_schema.assert_called_once()
        mock_extractor_service_instance.extract_metadata_from_job_url.assert_called_once_with(
            "https://example.com/job",
            mock_database_schema,
            "gpt-4o",
        )
        mock_convert.assert_called_once_with(mock_extracted_metadata, mock_database_schema)
        mock_display_results.assert_called_once_with(mock_extracted_metadata)

    @patch("src.main.Settings", autospec=True)
    @patch("src.main.parse_arguments")
    def test_main_missing_job_url(self, mock_parse_arguments: MagicMock, mock_settings: MagicMock) -> None:
        """Test main function exits when job URL is not provided."""
        mock_parse_arguments.side_effect = SystemExit(2)  # argparse exits with 2 for argument errors
        mock_settings_instance = MagicMock()
        mock_settings_instance.OPENAI_API_KEY = "test-openai-key"
        mock_settings_instance.NOTION_API_KEY = "test-notion-key"
        mock_settings_instance.NOTION_DATABASE_ID = "test-db-id"
        mock_settings_instance.LOG_LEVEL = "INFO"
        mock_settings.return_value = mock_settings_instance
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    @patch("src.main.Settings", autospec=True)
    @patch("src.main.parse_arguments")
    def test_main_settings_initialization_error(
        self, mock_parse_arguments: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test main function handles settings initialization errors."""
        mock_args = MagicMock()
        mock_args.job_url = "https://example.com/job"
        mock_args.model = "gpt-4o"
        mock_args.method = "openai_web_search"
        mock_parse_arguments.return_value = mock_args
        mock_settings.side_effect = Exception("Settings error")
        with pytest.raises(SystemExit):
            main()

    @patch("src.main.ExtractorService")
    @patch("src.main.NotionService")
    @patch("src.main.OpenAIClient")
    @patch("src.main.Settings")
    @patch("src.main.parse_arguments")
    def test_main_notion_service_error(
        self,
        mock_parse_arguments: MagicMock,
        mock_settings: MagicMock,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        mock_extractor_service: MagicMock,
    ) -> None:
        """Test main function handles Notion service errors."""
        # Setup argument mock
        mock_args = MagicMock()
        mock_args.job_url = "https://example.com/job"
        mock_args.model = "gpt-4o"
        mock_args.method = "openai_web_search"
        mock_parse_arguments.return_value = mock_args

        # Setup settings mock
        mock_settings_instance = MagicMock()
        mock_settings_instance.OPENAI_API_KEY = "test-openai-key"
        mock_settings_instance.NOTION_API_KEY = "test-notion-key"
        mock_settings_instance.NOTION_DATABASE_ID = "test-db-id"
        mock_settings_instance.LOG_LEVEL = "INFO"
        mock_settings.return_value = mock_settings_instance

        mock_notion_service_instance = MagicMock()
        mock_notion_service_instance.get_database_schema.side_effect = Exception("Notion API error")
        mock_notion_service.return_value = mock_notion_service_instance

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("src.main.ExtractorService")
    @patch("src.main.NotionService")
    @patch("src.main.OpenAIClient")
    @patch("src.main.Settings")
    @patch("src.main.parse_arguments")
    def test_main_extraction_error(
        self,
        mock_parse_arguments: MagicMock,
        mock_settings: MagicMock,
        mock_openai_client: MagicMock,
        mock_notion_service: MagicMock,
        mock_extractor_service: MagicMock,
    ) -> None:
        """Test main function handles extraction service errors."""
        # Setup argument mock
        mock_args = MagicMock()
        mock_args.job_url = "https://example.com/job"
        mock_args.model = "gpt-4o"
        mock_args.method = "openai_web_search"
        mock_parse_arguments.return_value = mock_args

        # Setup settings mock
        mock_settings_instance = MagicMock()
        mock_settings_instance.OPENAI_API_KEY = "test-openai-key"
        mock_settings_instance.NOTION_API_KEY = "test-notion-key"
        mock_settings_instance.NOTION_DATABASE_ID = "test-db-id"
        mock_settings_instance.LOG_LEVEL = "INFO"
        mock_settings.return_value = mock_settings_instance

        mock_notion_service_instance = MagicMock()
        mock_database_schema = {"job_title": {"type": "title"}}
        mock_notion_service_instance.get_database_schema.return_value = mock_database_schema
        mock_notion_service.return_value = mock_notion_service_instance

        mock_extractor_service_instance = MagicMock()
        mock_extractor_service_instance.extract_metadata_from_job_url.side_effect = Exception("Extraction error")
        mock_extractor_service.return_value = mock_extractor_service_instance

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


class TestDisplayResults:
    """Test the display_results function."""

    def test_display_results_basic_data(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test display_results with basic metadata."""
        extracted_metadata = {
            "job_title": "Software Engineer",
            "company": "Tech Corp",
            "salary": 100000,
            "is_remote": True,
        }

        display_results(extracted_metadata)

        captured = capsys.readouterr()
        output = captured.out

        # Check that the main sections are present
        assert "📊 EXTRACTED METADATA:" in output
        assert "EXTRACTED METADATA:" in output

        # Check that the extracted metadata is displayed
        assert "job_title: Software Engineer" in output
        assert "company: Tech Corp" in output
        assert "salary: 100000" in output
        assert "is_remote: True" in output

    def test_display_results_with_list_values(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test display_results with list values in metadata."""
        extracted_metadata = {
            "skills": ["Python", "JavaScript", "Docker"],
            "job_title": "Full Stack Developer",
        }

        display_results(extracted_metadata)

        captured = capsys.readouterr()
        output = captured.out

        # Check that list values are properly formatted
        assert "skills: Python, JavaScript, Docker" in output
        assert "job_title: Full Stack Developer" in output

    def test_display_results_empty_metadata(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test display_results with empty metadata."""
        extracted_metadata: dict[str, str] = {}

        display_results(extracted_metadata)

        captured = capsys.readouterr()
        output = captured.out

        # Check that the structure is still displayed even with empty data
        assert "📊 EXTRACTED METADATA:" in output
        assert "EXTRACTED METADATA:" in output

    def test_display_results_json_formatting(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that JSON is properly formatted in display_results."""
        extracted_metadata = {"test": "value"}

        display_results(extracted_metadata)

        captured = capsys.readouterr()
        output = captured.out

        # Verify that the extracted metadata is displayed
        assert "test: value" in output
