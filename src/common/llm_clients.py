"""
LLM Clients module for interacting with various language model providers.

This module provides client implementations for different LLM providers, starting with OpenAI.
"""

import json
from pathlib import Path
from typing import Any

import openai

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

    def get_response(self, prompt: str, model_name: str = "gpt-3.5-turbo") -> str:
        """Get a response from the specified OpenAI model using the Responses API.

        Args:
            prompt: The input prompt to send to the model.
            model_name: The name of the OpenAI model to use. Defaults to "gpt-3.5-turbo".

        Returns:
            The model's response as a string.

        Raises:
            openai.APIError: If there's an error communicating with the OpenAI API.
        """
        # Prepare the request body
        request_body: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1000,
        }

        # If we have a previous response ID, include it for stateful conversation
        if self.response_id:
            request_body["response_id"] = self.response_id

        try:
            # Make the API call
            response = self.client.responses.create(**request_body)

            # Store the response ID for the next interaction
            if hasattr(response, "id"):
                self.response_id = response.id

            # Check for error in response
            if hasattr(response, "error") and response.error:
                error_msg = f"API Error: {getattr(response.error, 'message', 'Unknown error')}"
                error_code = getattr(response.error, "code", None)
                if error_code:
                    error_msg += f" (code: {error_code})"
                raise ValueError(error_msg)

            # Extract the content from the response
            # The response structure can vary, so we need to check multiple possible locations
            if hasattr(response, "output"):
                # Case 1: Direct string output
                if isinstance(response.output, str):
                    return str(response.output)

                # Case 2: Output object with content
                if hasattr(response.output, "content"):
                    return str(response.output.content)

                # Case 3: Output with text property
                if hasattr(response.output, "text"):
                    return str(response.output.text)

                # Case 4: Output with output_text property
                if hasattr(response.output, "output_text"):
                    return str(response.output.output_text)

            # Case 5: Check for choices array (compatibility with chat completions format)
            if hasattr(response, "choices") and response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    return str(choice.message.content)
                if hasattr(choice, "text"):
                    return str(choice.text)

            # If we get here, we couldn't extract any content
            return ""

        except Exception as e:
            # Handle any exceptions during API call or response processing
            error_msg = f"Error getting response: {str(e)}"
            raise ValueError(error_msg) from e

    def extract_structured_data_from_url(
        self,
        url: str,
        extraction_schema: dict[str, Any],
        model_name: str = "gpt-4-1106-preview",
    ) -> dict[str, Any]:
        """Extract structured data from a URL using web search and structured outputs.

        Args:
            url: The URL to extract data from.
            extraction_schema: OpenAI JSON Schema defining the expected output structure.
            model_name: The name of the OpenAI model to use. Defaults to "gpt-4-1106-preview".

        Returns:
            Structured data extracted from the URL content.

        Raises:
            ValueError: If there's an error with the API call or response parsing.
        """
        # Load the prompt from file
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "sys_prompt_extract_metadata.txt"
        system_prompt = read_file_content(prompt_path)
        user_prompt = f"URL: {url}"

        # Ensure all fields are required and additionalProperties is false
        schema_copy = extraction_schema.copy()
        if "properties" in schema_copy:
            schema_copy["required"] = list(schema_copy["properties"].keys())
        schema_copy["additionalProperties"] = False

        # Prepare the request body with web search tool and structured outputs
        request_body: dict[str, Any] = {
            "model": model_name,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "tools": [{"type": "web_search"}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "structured_output",
                    "strict": True,
                    "schema": schema_copy,
                }
            },
            "temperature": 0.1,  # Lower temperature for more consistent extraction
        }

        # If we have a previous response ID, include it for stateful conversation
        if self.response_id:
            request_body["response_id"] = self.response_id

        try:
            # Make the API call
            response = self.client.responses.create(**request_body)

            # Store the response ID for the next interaction
            if hasattr(response, "id"):
                self.response_id = response.id

            # Check for error in response
            if hasattr(response, "error") and response.error:
                error_msg = f"API Error: {getattr(response.error, 'message', 'Unknown error')}"
                error_code = getattr(response.error, "code", None)
                if error_code:
                    error_msg += f" (code: {error_code})"
                raise ValueError(error_msg)

            # Extract the structured content from the response using output_text
            if hasattr(response, "output_text") and response.output_text:
                try:
                    structured_data = json.loads(response.output_text)
                    if isinstance(structured_data, dict):
                        return structured_data
                    else:
                        raise ValueError("Response is not a valid JSON object")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse structured output as JSON: {str(e)}") from e

            # Fallback: if structure doesn't match expected format
            raise ValueError("No valid structured output found in response")

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            # Handle any exceptions during API call or response processing
            error_msg = f"Error extracting structured data from URL: {str(e)}"
            raise ValueError(error_msg) from e
