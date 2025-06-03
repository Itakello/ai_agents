"""
LLM Clients module for interacting with various language model providers.

This module provides client implementations for different LLM providers, starting with OpenAI.
"""

import json
from typing import Any

import openai
from openai import NOT_GIVEN
from openai.types.responses import (
    ResponseInputItemParam,
    ResponseInputParam,
    ResponseTextConfigParam,
    WebSearchToolParam,
)


class OpenAIClient:
    """Client for interacting with OpenAI's Responses API.

    This client provides a simple interface to interact with OpenAI's models
    using the Responses API, which is a stateful API that combines chat completions
    and assistants API features.

    Args:
        api_key: The OpenAI API key for authentication.
    """

    def __init__(self, api_key: str, temperature: float = 0.7) -> None:
        """Initialize the OpenAI client with the provided API key and temperature.

        Args:
            api_key: The OpenAI API key for authentication.
            temperature: The temperature for model responses (default: 0.7).
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.response_id: str | None = None
        self.temperature: float = temperature

    def _create_messages(self, sys_prompt: str | None, user_prompt: str | None) -> ResponseInputParam:
        """Create a list of messages for the OpenAI API.

        Args:
            sys_prompt: The system prompt to include in the messages.
            user_prompt: The user prompt to include in the messages.

        Returns:
            A list of message dictionaries formatted for the OpenAI API.

        Raises:
            ValueError: If both sys_prompt and user_prompt are None.
        """
        if sys_prompt is None and user_prompt is None:
            raise ValueError("At least one of sys_prompt or user_prompt must be provided (not both None).")
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
            ValueError: If both sys_prompt and user_prompt are None.
            openai.APIError: If there's an error communicating with the OpenAI API.
        """

        messages = self._create_messages(sys_prompt, user_prompt)

        try:
            # Make the API call using proper parameter names
            response = self.client.responses.create(
                input=messages,
                model=model_name,
                temperature=self.temperature,
                previous_response_id=self.response_id if self.response_id else NOT_GIVEN,
            )

            if not hasattr(response, "id"):
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
        self,
        sys_prompt: str | None,
        user_prompt: str | None,
        model_name: str,
        schema: dict[str, Any],
        use_web_search: bool = False,
    ) -> dict[str, Any]:
        """Get a structured response from the specified OpenAI model using the Responses API.

        Args:
            sys_prompt: The system prompt to send to the model.
            user_prompt: The user prompt to send to the model.
            model_name: The name of the OpenAI model to use.
            schema: OpenAI JSON Schema defining the expected output structure.
            use_web_search: Whether to enable web search tools (defaults to False).

        Returns:
            Structured data extracted from the model's response.

        Raises:
            ValueError: If both sys_prompt and user_prompt are None.
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
            # Prepare tools parameter
            tools = (
                [WebSearchToolParam(type="web_search_preview", search_context_size="high", user_location=None)]
                if use_web_search
                else NOT_GIVEN
            )

            # Make the API call using proper parameter names
            response = self.client.responses.create(
                input=messages,
                model=model_name,
                text=text_config,
                temperature=self.temperature,
                previous_response_id=self.response_id if self.response_id else NOT_GIVEN,
                tools=tools,
            )

            if not hasattr(response, "id"):
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

            return dict(json.loads(response.output_text)) if response.output_text else {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse structured output as JSON: {str(e)}") from e
