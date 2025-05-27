"""
Tests for common utility functions.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.common import utils


def test_read_file_content() -> None:
    """Test reading content from a file."""
    # Create a temporary file with test content
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
        test_content = "Test file content"
        f.write(test_content)
        temp_path = f.name

    try:
        # Test reading with string path
        assert utils.read_file_content(temp_path) == test_content

        # Test reading with Path object
        assert utils.read_file_content(Path(temp_path)) == test_content
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_read_file_content_nonexistent() -> None:
    """Test reading from a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        utils.read_file_content("/nonexistent/path/to/file.txt")


def test_write_file_content() -> None:
    """Test writing content to a file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "test_file.txt"
        test_content = "Test content to write"

        # Test writing to a new file
        utils.write_file_content(file_path, test_content)
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == test_content

        # Test overwriting existing file
        new_content = "Updated content"
        utils.write_file_content(file_path, new_content)
        assert file_path.read_text(encoding="utf-8") == new_content


def test_write_file_content_creates_directories() -> None:
    """Test that write_file_content creates parent directories if they don't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a nested directory path
        nested_dir = Path(temp_dir) / "nested" / "subdirectory"
        file_path = nested_dir / "test_file.txt"

        # Write to the file (parent directories don't exist yet)
        test_content = "Test content"
        utils.write_file_content(file_path, test_content)

        # Verify the file was created with the correct content
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == test_content
