"""
Tests for common utility functions.
"""

import os
import tempfile
from datetime import datetime
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


def test_replace_prompt_placeholders_with_current_date() -> None:
    """Test that replace_prompt_placeholders correctly inserts current date."""
    template = "Today is {{CURRENT_DATE}}. Please process this request."
    result = utils.replace_prompt_placeholders(template)

    # Check that the current date placeholder was replaced
    assert "{{CURRENT_DATE}}" not in result
    assert "Today is" in result

    # Verify the date format matches expected pattern (e.g., "June 1, 2025")
    current_date = datetime.now().strftime("%B %d, %Y")
    assert current_date in result


def test_replace_prompt_placeholders_with_additional_kwargs() -> None:
    """Test replace_prompt_placeholders with additional keyword arguments."""
    template = "Date: {{CURRENT_DATE}}. URL: {{URL}}. Content: {{CONTENT}}."
    result = utils.replace_prompt_placeholders(
        template,
        URL="https://example.com",
        CONTENT="Sample content",
    )

    # Check all placeholders were replaced
    assert "{{CURRENT_DATE}}" not in result
    assert "{{URL}}" not in result
    assert "{{CONTENT}}" not in result

    # Check values were inserted correctly
    assert "https://example.com" in result
    assert "Sample content" in result

    current_date = datetime.now().strftime("%B %d, %Y")
    assert current_date in result


def test_replace_prompt_placeholders_with_no_placeholders() -> None:
    """Test replace_prompt_placeholders with a template that has no placeholders."""
    template = "This is a simple prompt with no placeholders."
    result = utils.replace_prompt_placeholders(template)

    # Should return the original template unchanged
    assert result == template


def test_replace_prompt_placeholders_partial_replacement() -> None:
    """Test that only specified placeholders are replaced."""
    template = "Date: {{CURRENT_DATE}}. URL: {{URL}}. Missing: {{MISSING}}."
    result = utils.replace_prompt_placeholders(template, URL="https://test.com")

    # Current date and URL should be replaced
    assert "{{CURRENT_DATE}}" not in result
    assert "{{URL}}" not in result
    assert "https://test.com" in result

    # MISSING placeholder should remain unchanged
    assert "{{MISSING}}" in result
