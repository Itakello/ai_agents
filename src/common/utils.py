"""
Utility functions for common file I/O operations.
"""

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
