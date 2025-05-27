"""
LLM Clients module for interacting with various language model providers.

This module provides client implementations for different LLM providers, starting with OpenAI.
"""

import json
from pathlib import Path
from typing import Any

import openai
from openai import NOT_GIVEN
from openai.types.responses import ResponseInputItemParam, ResponseTextConfigParam

from .utils import read_file_content


class OpenAIClient:
    """Client for interacting with OpenAI's Responses API.

    This client provides a simple interface to interact with OpenAI's models
    using the Responses API, which is a stateful API that combines chat completions
    and assistants API features.

    Args:
        api_key: The OpenAI API key for authentication.
    """

    def __init__(self, api_key: str) -> None:
        """Initialize the OpenAI client with the provided API key."""
        self.client = openai.OpenAI(api_key=api_key)
        self.response_id: str | None = None

    def _create_messages(self, sys_prompt: str | None, user_prompt: str | None) -> list[ResponseInputItemParam]:
        """Create a list of messages for the OpenAI API.

        Args:
            sys_prompt: The system prompt to include in the messages.
            user_prompt: The user prompt to include in the messages.

        Returns:
            A list of message dictionaries formatted for the OpenAI API.
        """
        messages: list[ResponseInputItemParam] = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})
        return messages

    def get_response(self, sys_prompt: str | None, user_prompt: str | None, model_name: str) -> str:
        """Get a response from the specified OpenAI model using the Responses API.

        Args:
            sys_prompt: The system prompt to send to the model.
            user_prompt: The user prompt to send to the model.
            model_name: The name of the OpenAI model to use.

        Returns:
            The model's response as a string.

        Raises:
            openai.APIError: If there's an error communicating with the OpenAI API.
        """

        messages = self._create_messages(sys_prompt, user_prompt)

        try:
            # Make the API call using proper parameter names
            response = self.client.responses.create(
                input=messages,
                model=model_name,
                temperature=0.7,
                previous_response_id=self.response_id if self.response_id else NOT_GIVEN,
            )

            if not hasattr(response, 'id'):
                raise ValueError(f"Unexpected response type: {type(response)}")

            self.response_id = response.id

            # Check for error in response
            if response.error:
                error_msg = f"API Error: {getattr(response.error, 'message', 'Unknown error')}"
                error_code = getattr(response.error, "code", None)
                if error_code:
                    error_msg += f" (code: {error_code})"
                raise ValueError(error_msg)

            return response.output_text.strip() if response.output_text else ""

        except Exception as e:
            # Handle any exceptions during API call or response processing
            error_msg = f"Error getting response: {str(e)}"
            raise ValueError(error_msg) from e

    def get_structured_response(
        self, sys_prompt: str | None, user_prompt: str | None, model_name: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Get a structured response from the specified OpenAI model using the Responses API.

        Args:
            sys_prompt: The system prompt to send to the model.
            user_prompt: The user prompt to send to the model.
            model_name: The name of the OpenAI model to use.
            schema: OpenAI JSON Schema defining the expected output structure.

        Returns:
            Structured data extracted from the model's response.

        Raises:
            ValueError: If there's an error with the API call or response parsing.
        """

        # Ensure all fields are required and additionalProperties is false
        schema_copy = schema.copy()

        messages = self._create_messages(sys_prompt, user_prompt)

        # Create the text configuration for structured output
        text_config: ResponseTextConfigParam = {
            "format": {
                "type": "json_schema",
                "name": "structured_response",
                "strict": True,
                "schema": schema_copy,
            }
        }

        try:
            # Make the API call using proper parameter names
            response = self.client.responses.create(
                input=messages,
                model=model_name,
                text=text_config,
                temperature=0.1,  # Lower temperature for more consistent extraction
                previous_response_id=self.response_id if self.response_id else NOT_GIVEN,
            )

            if not hasattr(response, 'id'):
                raise ValueError(f"Unexpected response type: {type(response)}")

            # Store the response ID for the next interaction
            self.response_id = response.id

            # Check for error in response
            if response.error:
                error_msg = f"API Error: {getattr(response.error, 'message', 'Unknown error')}"
                error_code = getattr(response.error, "code", None)
                if error_code:
                    error_msg += f" (code: {error_code})"
                raise ValueError(error_msg)

            return json.loads(response.output_text) if response.output_text else {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse structured output as JSON: {str(e)}") from e

    def extract_structured_data_from_url(
        self,
        url: str,
        extraction_schema: dict[str, Any],
        model_name: str,
    ) -> dict[str, Any]:
        """Extract structured data from a URL using web search and structured outputs.

        Args:
            url: The URL to extract data from.
            extraction_schema: OpenAI JSON Schema defining the expected output structure.
            model_name: The name of the OpenAI model to use.

        Returns:
            Structured data extracted from the URL content.

        Raises:
            ValueError: If there's an error with the API call or response parsing.
        """
        # Load the prompt from file
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "sys_prompt_extract_metadata.txt"
        sys_prompt = read_file_content(prompt_path)
        user_prompt = f"URL: {url}"

        return self.get_structured_response(
            sys_prompt=sys_prompt, user_prompt=user_prompt, model_name=model_name, schema=extraction_schema
        )
