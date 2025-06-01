"""
Utility functions for common file I/O operations.
"""

from datetime import datetime
from pathlib import Path
from typing import Union


def read_file_content(file_path: Union[str, Path]) -> str:
    """
    Read the entire content of a file as a string.

    Args:
        file_path: Path to the file to read. Can be a string or Path object.

    Returns:
        str: The content of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there is an error reading the file.
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {path}") from e
    except Exception as e:
        raise IOError(f"Error reading file {path}: {e}") from e


def write_file_content(file_path: Union[str, Path], content: str) -> None:
    """
    Write content to a file, creating parent directories if they don't exist.

    Args:
        file_path: Path where the file should be written. Can be a string or Path object.
        content: The content to write to the file.

    Raises:
        IOError: If there is an error writing to the file.
    """
    path = Path(file_path) if isinstance(file_path, str) else file_path
    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise IOError(f"Error writing to file {path}: {e}") from e


def replace_prompt_placeholders(prompt_template: str, **kwargs: str) -> str:
    """
    Replace placeholders in a prompt template with dynamic values.

    Automatically includes the current date as {{CURRENT_DATE}}.

    Args:
        prompt_template: The prompt template string with placeholders.
        **kwargs: Additional key-value pairs to replace in the template.

    Returns:
        str: The prompt with placeholders replaced.

    Example:
        >>> template = "Today is {{CURRENT_DATE}}. Process {{URL}}."
        >>> replace_prompt_placeholders(template, URL="https://example.com")
        "Today is December 15, 2024. Process https://example.com."
    """
    # Get current date in a readable format
    current_date = datetime.now().strftime("%B %d, %Y")

    # Start with the template
    result = prompt_template

    # Replace current date placeholder
    result = result.replace("{{CURRENT_DATE}}", current_date)

    # Replace any additional placeholders
    for key, value in kwargs.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, value)

    return result
