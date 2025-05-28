"""Tests for the LLM clients module."""

from typing import Generator
from unittest.mock import MagicMock, patch

import openai
import pytest

from src.common.llm_clients import OpenAIClient


class TestOpenAIClient:
    """Test suite for the OpenAIClient class."""

    @pytest.fixture
    def mock_openai_client(self) -> Generator[MagicMock, None, None]:
        """Create a mock OpenAI client with realistic response structure from API docs."""
        with patch("openai.OpenAI") as mock_client:
            # Real OpenAI Responses API structure
            mock_response = type(
                "Response",
                (),
                {
                    "id": "resp_test123",
                    "object": "response",
                    "created_at": 1741476542,
                    "status": "completed",
                    "error": None,
                    "output_text": "Test response",
                },
            )()

            mock_client.return_value.responses.create.return_value = mock_response
            yield mock_client

    def test_init_sets_up_client(self, mock_openai_client: MagicMock) -> None:
        """Test that the OpenAI client is initialized with the correct API key."""
        # Arrange
        api_key = "test-api-key"

        # Act
        client = OpenAIClient(api_key=api_key)

        # Assert
        mock_openai_client.assert_called_once_with(api_key=api_key)
        assert client.response_id is None

    def test_get_response_calls_api_correctly(self, mock_openai_client: MagicMock) -> None:
        """Test that get_chat_completion calls the Responses API correctly."""
        # Arrange
        api_key = "test-api-key"
        prompt = "Test prompt"
        model_name = "gpt-4"

        # Get the mock responses client
        mock_responses = mock_openai_client.return_value.responses

        # Act
        client = OpenAIClient(api_key=api_key)
        response = client.get_response(sys_prompt=None, user_prompt=prompt, model_name=model_name)

        # Assert
        mock_responses.create.assert_called_once()
        call_args = mock_responses.create.call_args[1]

        assert call_args["model"] == model_name
        assert call_args["input"] == [{"role": "user", "content": prompt}]
        assert call_args["temperature"] == 0.7

        assert call_args["previous_response_id"] == openai.NOT_GIVEN
        assert response == "Test response"
        assert client.response_id == "resp_test123"  # Should be set after first call

    def test_get_chat_completion_handles_empty_response(self, mock_openai_client: MagicMock) -> None:
        """Test that get_chat_completion handles empty responses gracefully."""
        # Arrange
        api_key = "test-api-key"
        prompt = "Test prompt"

        # Create a response with empty output
        empty_response = type("Response", (), {"id": "resp_empty", "error": None, "output_text": ""})()

        mock_openai_client.return_value.responses.create.return_value = empty_response

        # Act
        client = OpenAIClient(api_key=api_key)
        response = client.get_response(sys_prompt=None, user_prompt=prompt, model_name="gpt-4o")

        # Assert
        assert response == ""

    def test_get_chat_completion_uses_default_model(self, mock_openai_client: MagicMock) -> None:
        """Test that get_chat_completion uses the default model when none is specified."""
        # Arrange
        api_key = "test-api-key"
        prompt = "Test prompt"

        # Act
        client = OpenAIClient(api_key=api_key)

        client.get_response(sys_prompt=None, user_prompt=prompt, model_name="gpt-4o")

        # Assert
        call_args = mock_openai_client.return_value.responses.create.call_args[1]
        assert call_args["model"] == "gpt-4o"

    def test_get_chat_completion_handles_api_errors(self, mock_openai_client: MagicMock) -> None:
        """Test that get_chat_completion properly handles API errors."""
        # Test 1: API returns an error object
        error_response = type(
            "Response",
            (),
            {
                "id": "resp_error",
                "error": type("Error", (), {"message": "Test error message", "code": "test_error_code"})(),
            },
        )()

        mock_openai_client.return_value.responses.create.return_value = error_response

        client = OpenAIClient(api_key="test-api-key")

        with pytest.raises(ValueError) as exc_info:
            client.get_response(sys_prompt=None, user_prompt="Test prompt", model_name="gpt-4o")

        assert "API Error: Test error message (code: test_error_code)" in str(exc_info.value)

        # Test 2: Exception during API call
        mock_openai_client.return_value.responses.create.side_effect = Exception("Connection error")

        with pytest.raises(ValueError) as exc_info:
            client.get_response(sys_prompt=None, user_prompt="Test prompt", model_name="gpt-4o")

        assert "Error getting response: Connection error" in str(exc_info.value)

    def test_extract_structured_data_from_url_success(self, mock_openai_client: MagicMock) -> None:
        """Test successful structured data extraction from URL."""
        # Arrange
        api_key = "test-api-key"
        url = "https://example.com/job"
        schema = {
            "type": "object",
            "properties": {
                "job_title": {"type": "string"},
                "company": {"type": "string"},
            },
        }

        # Create mock response with output_text
        mock_response = type(
            "Response",
            (),
            {
                "id": "resp_test123",
                "error": None,
                "output_text": '{"job_title": "Software Engineer", "company": "Tech Corp"}',
            },
        )()
        mock_openai_client.return_value.responses.create.return_value = mock_response

        # Act
        client = OpenAIClient(api_key=api_key)
        result = client.extract_structured_data_from_url(url, schema, model_name="gpt-4o")

        # Assert
        assert result == {"job_title": "Software Engineer", "company": "Tech Corp"}

        # Verify API call
        call_args = mock_openai_client.return_value.responses.create.call_args[1]
        assert call_args["model"] == "gpt-4o"
        assert len(call_args["input"]) == 1
        assert call_args["input"][0]["role"] == "system"
        assert url in call_args["input"][0]["content"]
        assert call_args["text"]["format"]["type"] == "json_schema"
        assert call_args["text"]["format"]["strict"] is True

    def test_extract_structured_data_handles_invalid_json(self, mock_openai_client: MagicMock) -> None:
        """Test that extract_structured_data_from_url handles invalid JSON responses."""
        # Arrange
        api_key = "test-api-key"
        url = "https://example.com/job"
        schema = {"type": "object", "properties": {"job_title": {"type": "string"}}}

        # Create mock response with invalid JSON
        mock_response = type(
            "Response",
            (),
            {
                "id": "resp_test123",
                "error": None,
                "output_text": "invalid json response",
            },
        )()
        mock_openai_client.return_value.responses.create.return_value = mock_response

        # Act & Assert
        client = OpenAIClient(api_key=api_key)
        with pytest.raises(ValueError) as exc_info:
            client.extract_structured_data_from_url(url, schema, model_name="gpt-4o")

        assert "Failed to parse structured output as JSON" in str(exc_info.value)

    def test_extract_structured_data_handles_missing_output_text(self, mock_openai_client: MagicMock) -> None:
        """Test that extract_structured_data_from_url handles missing output_text."""
        # Arrange
        api_key = "test-api-key"
        url = "https://example.com/job"
        schema = {"type": "object", "properties": {"job_title": {"type": "string"}}}

        # Create mock response without output_text
        mock_response = type("Response", (), {"id": "resp_test123", "error": None, "output_text": None})()
        mock_openai_client.return_value.responses.create.return_value = mock_response

        # Act & Assert
        client = OpenAIClient(api_key=api_key)
        result = client.extract_structured_data_from_url(url, schema, model_name="gpt-4o")

        assert result == {}
