"""Tests for the OpenAI service module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import openai
import pytest

from src.common.services.openai_service import OpenAIService


class TestOpenAIService:
    """Test suite for the OpenAIService class."""

    @pytest.fixture
    def mock_client(self) -> Generator[MagicMock]:
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

    def test_init_sets_up_client(self, mock_client: MagicMock) -> None:
        """Test that the OpenAI service is initialized with the correct API key."""
        # Arrange
        api_key = "test-api-key"

        # Act
        service = OpenAIService(api_key=api_key, temperature=0.7)

        # Assert
        mock_client.assert_called_once_with(api_key=api_key)
        assert service.response_id is None

    def test_get_response_calls_api_correctly(self, mock_client: MagicMock) -> None:
        """Test that get_chat_completion calls the Responses API correctly."""
        # Arrange
        api_key = "test-api-key"
        prompt = "Test prompt"
        model_name = "gpt-4"

        # Get the mock responses client
        mock_responses = mock_client.return_value.responses

        # Act
        service = OpenAIService(api_key=api_key, temperature=0.7)
        response = service.get_response(sys_prompt=None, user_prompt=prompt, model_name=model_name)

        # Assert
        mock_responses.create.assert_called_once()
        call_args = mock_responses.create.call_args[1]

        assert call_args["model"] == model_name
        assert call_args["input"] == [{"role": "user", "content": prompt}]
        assert call_args["temperature"] == 0.7

        assert call_args["previous_response_id"] == openai.NOT_GIVEN
        assert response == "Test response"
        assert service.response_id == "resp_test123"  # Should be set after first call

    def test_get_response_raises_if_both_prompts_none(self, mock_client: MagicMock) -> None:
        """Test that get_response raises ValueError if both sys_prompt and user_prompt are None."""
        service = OpenAIService(api_key="test-api-key", temperature=0.7)
        with pytest.raises(ValueError, match="At least one of sys_prompt or user_prompt must be provided"):
            service.get_response(sys_prompt=None, user_prompt=None, model_name="gpt-4")

    def test_get_structured_response_raises_if_both_prompts_none(self, mock_client: MagicMock) -> None:
        """Test that get_structured_response raises ValueError if both sys_prompt and user_prompt are None."""
        service = OpenAIService(api_key="test-api-key", temperature=0.7)
        schema = {"type": "object", "properties": {"foo": {"type": "string"}}, "required": ["foo"]}
        with pytest.raises(ValueError, match="At least one of sys_prompt or user_prompt must be provided"):
            service.get_structured_response(sys_prompt=None, user_prompt=None, model_name="gpt-4", schema=schema)

    def test_get_response_handles_empty_response(self, mock_client: MagicMock) -> None:
        """Test that get_response handles empty responses gracefully."""
        # Arrange
        api_key = "test-api-key"
        prompt = "Test prompt"

        # Create a response with empty output
        empty_response = type("Response", (), {"id": "resp_empty", "error": None, "output_text": ""})()

        mock_client.return_value.responses.create.return_value = empty_response

        # Act
        service = OpenAIService(api_key=api_key, temperature=0.7)
        response = service.get_response(sys_prompt=None, user_prompt=prompt, model_name="gpt-4o")

        # Assert
        assert response == ""

    def test_get_response_uses_default_model(self, mock_client: MagicMock) -> None:
        """Test that get_response uses the default model when none is specified."""
        # Arrange
        api_key = "test-api-key"
        prompt = "Test prompt"

        # Act
        service = OpenAIService(api_key=api_key, temperature=0.7)

        service.get_response(sys_prompt=None, user_prompt=prompt, model_name="gpt-4o")

        # Assert
        call_args = mock_client.return_value.responses.create.call_args[1]
        assert call_args["model"] == "gpt-4o"

    def test_get_response_handles_api_errors(self, mock_client: MagicMock) -> None:
        """Test that get_response properly handles API errors."""
        # Test 1: API returns an error object
        error_response = type(
            "Response",
            (),
            {
                "id": "resp_error",
                "error": type("Error", (), {"message": "Test error message", "code": "test_error_code"})(),
            },
        )()

        mock_client.return_value.responses.create.return_value = error_response

        service = OpenAIService(api_key="test-api-key", temperature=0.7)

        with pytest.raises(ValueError) as exc_info:
            service.get_response(sys_prompt=None, user_prompt="Test prompt", model_name="gpt-4o")

        assert "API Error: Test error message (code: test_error_code)" in str(exc_info.value)

        # Test 2: Exception during API call
        mock_client.return_value.responses.create.side_effect = Exception("Connection error")

        with pytest.raises(ValueError) as exc_info:
            service.get_response(sys_prompt=None, user_prompt="Test prompt", model_name="gpt-4o")

        assert "Error getting response: Connection error" in str(exc_info.value)
