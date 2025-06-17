"""Tests for the database schema verification functionality."""

import pytest

from src.common.database_verifier import DatabaseVerifier
from src.common.models import NotionDatabaseSchemaProperty


class TestDatabaseVerifier:
    """Test cases for database schema verification."""

    @pytest.fixture
    def verifier(self) -> DatabaseVerifier:
        """Create a DatabaseVerifier instance."""
        return DatabaseVerifier()

    def test_check_schema_missing_properties(self, verifier: DatabaseVerifier) -> None:
        """Test that missing properties are correctly identified."""
        schema = {
            "properties": {
                "Title": {"type": "title", "name": "Title"},
                "Company": {"type": "rich_text", "name": "Company"},
            }
        }
        missing_props, type_mismatches = verifier.check_schema(schema)
        assert missing_props == {"Job URL", "Resume"}
        assert not type_mismatches

    def test_check_schema_type_mismatches(self, verifier: DatabaseVerifier) -> None:
        """Test that type mismatches are correctly identified."""
        schema = {
            "properties": {
                "Title": {"type": "title", "name": "Title"},
                "Company": {"type": "rich_text", "name": "Company"},
                "Job URL": {"type": "rich_text", "name": "Job URL"},  # Should be "url"
                "Resume": {"type": "rich_text", "name": "Resume"},  # Should be "files"
            }
        }
        missing_props, type_mismatches = verifier.check_schema(schema)
        assert not missing_props
        assert type_mismatches == {"Job URL": "rich_text", "Resume": "rich_text"}

    def test_fix_schema_adds_missing_properties(self, verifier: DatabaseVerifier) -> None:
        """Test that missing properties are added correctly."""
        schema = {
            "properties": {
                "Title": {"type": "title", "name": "Title"},
                "Company": {"type": "rich_text", "name": "Company"},
            }
        }
        missing_props: set[str] = {"Job URL", "Resume"}
        type_mismatches: dict[str, str] = {}
        fixed_schema = verifier.fix_schema(schema, missing_props, type_mismatches)
        properties = fixed_schema["properties"]
        assert "Job URL" in properties
        assert properties["Job URL"]["type"] == "url"
        assert "Resume" in properties
        assert properties["Resume"]["type"] == "files"

    def test_fix_schema_corrects_type_mismatches(self, verifier: DatabaseVerifier) -> None:
        """Test that type mismatches are corrected."""
        schema = {
            "properties": {
                "Title": {"type": "title", "name": "Title"},
                "Company": {"type": "rich_text", "name": "Company"},
                "Job URL": {"type": "rich_text", "name": "Job URL"},
                "Resume": {"type": "rich_text", "name": "Resume"},
            }
        }
        missing_props: set[str] = set()
        type_mismatches: dict[str, str] = {"Job URL": "rich_text", "Resume": "rich_text"}
        fixed_schema = verifier.fix_schema(schema, missing_props, type_mismatches)
        properties = fixed_schema["properties"]
        assert properties["Job URL"]["type"] == "url"
        assert properties["Resume"]["type"] == "files"

    def test_validate_property_success(self, verifier: DatabaseVerifier) -> None:
        """Test successful property validation."""
        property_data = {
            "id": "test_id",
            "name": "Test Property",
            "type": "rich_text",
        }
        result = verifier.validate_property(property_data)
        assert isinstance(result, NotionDatabaseSchemaProperty)
        assert result.id == "test_id"
        assert result.name == "Test Property"
        assert result.type == "rich_text"

    def test_validate_property_invalid_data(self, verifier: DatabaseVerifier) -> None:
        """Test property validation with invalid data."""
        property_data = {
            "name": "Test Property",  # Missing required 'id' field
            "type": "rich_text",
        }
        with pytest.raises(ValueError, match="Invalid property data"):
            verifier.validate_property(property_data)
