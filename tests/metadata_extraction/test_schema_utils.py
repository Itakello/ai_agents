"""Tests for metadata extraction models and conversion functions."""

from typing import Any
from unittest.mock import patch

from src.metadata_extraction.schema_utils import (
    _generate_example_description,
    _should_exclude_property,
    _should_keep_options,
    convert_openai_response_to_notion_update,
    create_openai_schema_from_notion_database,
    notion_property_to_openai_schema,
    openai_data_to_notion_property,
)


class TestHelperFunctions:
    """Test the private helper functions."""

    def test_should_exclude_property_readonly_types(self) -> None:
        """Test exclusion of read-only property types."""
        assert _should_exclude_property("created_time", "")
        assert _should_exclude_property("created_by", "")
        assert _should_exclude_property("last_edited_time", "")
        assert _should_exclude_property("last_edited_by", "")
        assert _should_exclude_property("formula", "")
        assert _should_exclude_property("rollup", "")

    def test_should_exclude_property_exclude_directive(self) -> None:
        """Test exclusion based on #exclude directive."""
        assert _should_exclude_property("rich_text", "some description #exclude")
        assert _should_exclude_property("number", "#exclude at start")
        assert _should_exclude_property("select", "middle #exclude text")

    def test_should_exclude_property_normal_properties(self) -> None:
        """Test that normal properties are not excluded."""
        assert not _should_exclude_property("rich_text", "")
        assert not _should_exclude_property("number", "normal description")
        assert not _should_exclude_property("select", "description without directive")

    def test_should_keep_options_with_directive(self) -> None:
        """Test that #keep-options directive is detected."""
        assert _should_keep_options("some description #keep-options")
        assert _should_keep_options("#keep-options at start")
        assert _should_keep_options("middle #keep-options text")

    def test_should_keep_options_without_directive(self) -> None:
        """Test that properties without directive return False."""
        assert not _should_keep_options("")
        assert not _should_keep_options("normal description")
        assert not _should_keep_options("description with #other-directive")

    @patch("src.metadata_extraction.schema_utils.random.sample")
    def test_generate_example_description_with_options(self, mock_sample: Any) -> None:
        """Test example description generation with options."""
        options = [
            {"name": "Option1", "id": "1"},
            {"name": "Option2", "id": "2"},
            {"name": "Option3", "id": "3"},
        ]
        mock_sample.return_value = options[:2]  # Return first 2 options

        prop_config: dict[str, Any] = {"select": {"options": options}}
        result = _generate_example_description(prop_config, "select")

        assert result == "e.g. Option1, Option2, ..."
        mock_sample.assert_called_once_with(options, 3)  # Should sample min(3, len(options)) = 3

    def test_generate_example_description_empty_options(self) -> None:
        """Test example description generation with no options."""
        prop_config: dict[str, Any] = {"select": {"options": []}}
        result = _generate_example_description(prop_config, "select")
        assert result == ""

    def test_generate_example_description_missing_config(self) -> None:
        """Test example description generation with missing config."""
        prop_config: dict[str, Any] = {}
        result = _generate_example_description(prop_config, "select")
        assert result == ""


class TestNotionPropertyToOpenAISchema:
    """Test conversion from Notion property definitions to OpenAI JSON Schema."""

    def test_rich_text_property(self) -> None:
        notion_prop = {"type": "rich_text"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string", "maxLength": 2000}

    def test_title_property(self) -> None:
        notion_prop = {"type": "title"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string", "maxLength": 2000}

    def test_number_property(self) -> None:
        notion_prop = {"type": "number"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "number"}

    def test_checkbox_property(self) -> None:
        notion_prop = {"type": "checkbox"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "boolean"}

    def test_select_property_with_options(self) -> None:
        notion_prop = {
            "type": "select",
            "select": {
                "options": [
                    {"name": "Junior", "id": "1", "color": "blue"},
                    {"name": "Senior", "id": "2", "color": "red"},
                ]
            },
        }
        result = notion_property_to_openai_schema(notion_prop, add_options=True)
        assert result == {"type": "string", "enum": ["Junior", "Senior"]}

    def test_select_property_without_options(self) -> None:
        notion_prop = {"type": "select", "select": {}}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string"}

    def test_status_property_with_options(self) -> None:
        notion_prop = {
            "type": "status",
            "status": {
                "options": [
                    {"name": "Not started", "id": "1", "color": "default"},
                    {"name": "In progress", "id": "2", "color": "blue"},
                    {"name": "Done", "id": "3", "color": "green"},
                ]
            },
        }
        result = notion_property_to_openai_schema(notion_prop, add_options=True)
        assert result == {"type": "string", "enum": ["Not started", "In progress", "Done"]}

    def test_status_property_without_options(self) -> None:
        notion_prop = {"type": "status", "status": {}}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string"}

    def test_multi_select_property_with_options(self) -> None:
        notion_prop = {
            "type": "multi_select",
            "multi_select": {
                "options": [
                    {"name": "Python", "id": "1", "color": "blue"},
                    {"name": "JavaScript", "id": "2", "color": "red"},
                ]
            },
        }
        result = notion_property_to_openai_schema(notion_prop, add_options=True)
        assert result == {"type": "array", "items": {"type": "string", "enum": ["Python", "JavaScript"]}}

    def test_multi_select_property_without_options(self) -> None:
        notion_prop = {"type": "multi_select", "multi_select": {}}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_date_property(self) -> None:
        notion_prop = {"type": "date"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string", "format": "date"}

    def test_email_property(self) -> None:
        notion_prop = {"type": "email"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string", "format": "email"}

    def test_phone_number_property(self) -> None:
        notion_prop = {"type": "phone_number"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string"}

    def test_url_property(self) -> None:
        notion_prop = {"type": "url"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string", "pattern": r"^(https?)://[^\s/$.?#].[^\s]*$"}

    def test_people_property(self) -> None:
        notion_prop = {"type": "people"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_files_property(self) -> None:
        notion_prop = {"type": "files"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "array", "items": {"type": "string", "format": "uri"}}

    def test_unknown_property_type(self) -> None:
        notion_prop = {"type": "unknown_type"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string"}


class TestOpenAIDataToNotionProperty:
    """Test conversion from OpenAI response data to Notion property values."""

    def test_rich_text_conversion(self) -> None:
        result = openai_data_to_notion_property("Hello World", "rich_text")
        assert result == {"rich_text": [{"type": "text", "text": {"content": "Hello World"}}]}

    def test_title_conversion(self) -> None:
        result = openai_data_to_notion_property("Job Title", "title")
        assert result == {"title": [{"type": "text", "text": {"content": "Job Title"}}]}

    def test_number_conversion(self) -> None:
        result = openai_data_to_notion_property(42, "number")
        assert result == {"number": 42.0}

    def test_number_conversion_string_input(self) -> None:
        result = openai_data_to_notion_property("42.5", "number")
        assert result == {"number": 42.5}

    def test_checkbox_conversion_true(self) -> None:
        result = openai_data_to_notion_property(True, "checkbox")
        assert result == {"checkbox": True}

    def test_checkbox_conversion_false(self) -> None:
        result = openai_data_to_notion_property(False, "checkbox")
        assert result == {"checkbox": False}

    def test_select_conversion(self) -> None:
        result = openai_data_to_notion_property("Senior", "select")
        assert result == {"select": {"name": "Senior"}}

    def test_select_conversion_empty_value(self) -> None:
        result = openai_data_to_notion_property("", "select")
        assert result == {}

    def test_status_conversion(self) -> None:
        result = openai_data_to_notion_property("In progress", "status")
        assert result == {"status": {"name": "In progress"}}

    def test_status_conversion_empty_value(self) -> None:
        result = openai_data_to_notion_property("", "status")
        assert result == {}

    def test_multi_select_conversion(self) -> None:
        result = openai_data_to_notion_property(["Python", "JavaScript"], "multi_select")
        assert result == {"multi_select": [{"name": "Python"}, {"name": "JavaScript"}]}

    def test_multi_select_conversion_with_empty_items(self) -> None:
        result = openai_data_to_notion_property(["Python", "", "JavaScript", None], "multi_select")
        assert result == {"multi_select": [{"name": "Python"}, {"name": "JavaScript"}]}

    def test_multi_select_conversion_non_list(self) -> None:
        result = openai_data_to_notion_property("Python", "multi_select")
        assert result == {}

    def test_date_conversion(self) -> None:
        result = openai_data_to_notion_property("2023-12-25", "date")
        assert result == {"date": {"start": "2023-12-25"}}

    def test_email_conversion(self) -> None:
        result = openai_data_to_notion_property("test@example.com", "email")
        assert result == {"email": "test@example.com"}

    def test_phone_number_conversion(self) -> None:
        result = openai_data_to_notion_property("+1-555-123-4567", "phone_number")
        assert result == {"phone_number": "+1-555-123-4567"}

    def test_url_conversion(self) -> None:
        result = openai_data_to_notion_property("https://example.com", "url")
        assert result == {"url": "https://example.com"}

    def test_people_conversion(self) -> None:
        # People properties are complex and return empty for now
        result = openai_data_to_notion_property(["John Doe", "Jane Smith"], "people")
        assert result == {}

    def test_files_conversion(self) -> None:
        urls = ["https://example.com/file1.pdf", "https://example.com/file2.doc"]
        result = openai_data_to_notion_property(urls, "files")
        expected = {
            "files": [
                {"type": "external", "name": "file1.pdf", "external": {"url": "https://example.com/file1.pdf"}},
                {"type": "external", "name": "file2.doc", "external": {"url": "https://example.com/file2.doc"}},
            ]
        }
        assert result == expected

    def test_files_conversion_empty_list(self) -> None:
        result = openai_data_to_notion_property([], "files")
        assert result == {}

    def test_unknown_property_type(self) -> None:
        result = openai_data_to_notion_property("Some value", "unknown_type")
        assert result == {"rich_text": [{"text": {"content": "Some value"}}]}

    def test_none_value(self) -> None:
        result = openai_data_to_notion_property(None, "rich_text")
        assert result == {}


class TestCreateOpenAISchemaFromNotionDatabase:
    """Test creating complete OpenAI JSON Schema from Notion database properties."""

    def test_create_schema_basic_properties(self) -> None:
        notion_properties = {
            "job_title": {"type": "title"},
            "company": {"type": "rich_text"},
            "salary": {"type": "number"},
            "is_remote": {"type": "checkbox"},
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        expected = {
            "type": "object",
            "properties": {
                "job_title": {"type": "string", "maxLength": 2000},
                "company": {"type": "string", "maxLength": 2000},
                "salary": {"type": "number"},
                "is_remote": {"type": "boolean"},
            },
            "required": ["job_title", "company", "salary", "is_remote"],
            "additionalProperties": False,
        }
        assert result == expected

    def test_create_schema_skips_readonly_properties(self) -> None:
        notion_properties = {
            "job_title": {"type": "title"},
            "created_time": {"type": "created_time"},
            "created_by": {"type": "created_by"},
            "last_edited_time": {"type": "last_edited_time"},
            "last_edited_by": {"type": "last_edited_by"},
            "formula_field": {"type": "formula"},
            "rollup_field": {"type": "rollup"},
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        # Only job_title should be included
        expected = {
            "type": "object",
            "properties": {"job_title": {"type": "string", "maxLength": 2000}},
            "required": ["job_title"],
            "additionalProperties": False,
        }
        assert result == expected

    def test_create_schema_with_select_options(self) -> None:
        notion_properties = {
            "experience_level": {
                "type": "select",
                "select": {
                    "options": [
                        {"name": "Junior", "id": "1"},
                        {"name": "Mid", "id": "2"},
                        {"name": "Senior", "id": "3"},
                    ]
                },
            }
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=True).dict()

        expected = {
            "type": "object",
            "properties": {"experience_level": {"type": "string", "enum": ["Junior", "Mid", "Senior"]}},
            "required": ["experience_level"],
            "additionalProperties": False,
        }
        assert result == expected

    def test_create_schema_exclude_directive(self) -> None:
        """Test that properties with #exclude directive are skipped."""
        notion_properties = {
            "job_title": {"type": "title"},
            "internal_notes": {"type": "rich_text", "description": "Internal notes #exclude"},
            "company": {"type": "rich_text"},
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        expected = {
            "type": "object",
            "properties": {
                "job_title": {"type": "string", "maxLength": 2000},
                "company": {"type": "string", "maxLength": 2000},
            },
            "required": ["job_title", "company"],
            "additionalProperties": False,
        }
        assert result == expected

    def test_create_schema_keep_options_directive(self) -> None:
        """Test that #keep-options directive forces inclusion of enum options."""
        notion_properties = {
            "status": {
                "type": "select",
                "description": "Task status #keep-options",
                "select": {
                    "options": [
                        {"name": "Todo", "id": "1"},
                        {"name": "In Progress", "id": "2"},
                        {"name": "Done", "id": "3"},
                    ]
                },
            }
        }
        # Even with add_options=False, #keep-options should force inclusion
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        expected = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["Todo", "In Progress", "Done"],
                    "description": "Task status #keep-options",
                }
            },
            "required": ["status"],
            "additionalProperties": False,
        }
        assert result == expected

    @patch("src.metadata_extraction.schema_utils.random.sample")
    def test_create_schema_example_generation(self, mock_sample: Any) -> None:
        """Test that examples are generated for select properties when options not included."""
        mock_sample.return_value = [{"name": "Junior", "id": "1"}, {"name": "Senior", "id": "2"}]

        notion_properties = {
            "experience_level": {
                "type": "select",
                "select": {
                    "options": [
                        {"name": "Junior", "id": "1"},
                        {"name": "Mid", "id": "2"},
                        {"name": "Senior", "id": "3"},
                    ]
                },
            }
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        # Should generate example description
        assert "description" in result["properties"]["experience_level"]
        assert "e.g. Junior, Senior, ..." in result["properties"]["experience_level"]["description"]

    @patch("src.metadata_extraction.schema_utils.random.sample")
    def test_create_schema_preserve_original_description_with_examples(self, mock_sample: Any) -> None:
        """Test that original descriptions are preserved when adding examples."""
        mock_sample.return_value = [{"name": "Low", "id": "1"}, {"name": "High", "id": "2"}]

        notion_properties = {
            "priority": {
                "type": "select",
                "description": "Task priority level",
                "select": {
                    "options": [
                        {"name": "Low", "id": "1"},
                        {"name": "Medium", "id": "2"},
                        {"name": "High", "id": "3"},
                    ]
                },
            }
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        # Should combine original description with examples
        expected_desc = "Task priority level | e.g. Low, High, ..."
        assert result["properties"]["priority"]["description"] == expected_desc

    def test_create_schema_multi_select_example_generation(self) -> None:
        """Test example generation for multi_select properties."""
        notion_properties = {
            "skills": {
                "type": "multi_select",
                "multi_select": {
                    "options": [
                        {"name": "Python", "id": "1"},
                        {"name": "JavaScript", "id": "2"},
                        {"name": "Java", "id": "3"},
                        {"name": "Go", "id": "4"},
                    ]
                },
            }
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        # Should generate examples for multi_select
        assert "description" in result["properties"]["skills"]
        description = result["properties"]["skills"]["description"]
        assert "e.g." in description
        assert "..." in description

    def test_create_schema_status_example_generation(self) -> None:
        """Test example generation for status properties."""
        notion_properties = {
            "workflow_status": {
                "type": "status",
                "status": {
                    "options": [
                        {"name": "Draft", "id": "1"},
                        {"name": "Review", "id": "2"},
                        {"name": "Published", "id": "3"},
                    ]
                },
            }
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        # Should generate examples for status
        assert "description" in result["properties"]["workflow_status"]
        description = result["properties"]["workflow_status"]["description"]
        assert "e.g." in description
        assert "..." in description

    def test_create_schema_mixed_directives_and_types(self) -> None:
        """Test complex scenario with mixed property types and directives."""
        notion_properties = {
            "title": {"type": "title"},
            "description": {"type": "rich_text"},
            "priority": {
                "type": "select",
                "description": "Priority level #keep-options",
                "select": {"options": [{"name": "High", "id": "1"}, {"name": "Low", "id": "2"}]},
            },
            "tags": {
                "type": "multi_select",
                "multi_select": {"options": [{"name": "urgent", "id": "1"}, {"name": "bug", "id": "2"}]},
            },
            "internal_id": {
                "type": "number",
                "description": "Internal tracking #exclude",
            },
            "created_time": {"type": "created_time"},
            "is_public": {"type": "checkbox"},
        }
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False).dict()

        # Check what's included and excluded
        assert "title" in result["properties"]
        assert "description" in result["properties"]
        assert "priority" in result["properties"]  # Has #keep-options
        assert "tags" in result["properties"]  # Should have examples
        assert "is_public" in result["properties"]

        # Check what's excluded
        assert "internal_id" not in result["properties"]  # Has #exclude
        assert "created_time" not in result["properties"]  # Read-only type

        # Check that priority has enum options (due to #keep-options)
        assert "enum" in result["properties"]["priority"]
        assert result["properties"]["priority"]["enum"] == ["High", "Low"]

        # Check that tags has example description (no #keep-options)
        assert "description" in result["properties"]["tags"]

        # Verify required fields
        expected_required = ["title", "description", "priority", "tags", "is_public"]
        assert sorted(result["required"]) == sorted(expected_required)


class TestConvertOpenAIResponseToNotionUpdate:
    """Test converting OpenAI response to Notion page update format."""

    def test_convert_response_basic_types(self) -> None:
        openai_response = {
            "job_title": "Software Engineer",
            "salary": 75000,
            "is_remote": True,
        }
        notion_properties = {
            "job_title": {"type": "title"},
            "salary": {"type": "number"},
            "is_remote": {"type": "checkbox"},
        }

        result = convert_openai_response_to_notion_update(openai_response, notion_properties)

        expected = {
            "properties": {
                "job_title": {"title": [{"type": "text", "text": {"content": "Software Engineer"}}]},
                "salary": {"number": 75000.0},
                "is_remote": {"checkbox": True},
            }
        }
        assert result == expected

    def test_convert_response_skips_unknown_properties(self) -> None:
        openai_response = {
            "job_title": "Software Engineer",
            "unknown_field": "some value",
        }
        notion_properties = {"job_title": {"type": "title"}}

        result = convert_openai_response_to_notion_update(openai_response, notion_properties)

        expected = {
            "properties": {"job_title": {"title": [{"type": "text", "text": {"content": "Software Engineer"}}]}}
        }
        assert result == expected

    def test_convert_response_skips_none_values(self) -> None:
        openai_response = {
            "job_title": "Software Engineer",
            "salary": None,
        }
        notion_properties = {
            "job_title": {"type": "title"},
            "salary": {"type": "number"},
        }

        result = convert_openai_response_to_notion_update(openai_response, notion_properties)

        expected = {
            "properties": {"job_title": {"title": [{"type": "text", "text": {"content": "Software Engineer"}}]}}
        }
        assert result == expected

    def test_convert_response_with_multi_select(self) -> None:
        openai_response = {"skills": ["Python", "JavaScript", "Docker"]}
        notion_properties = {"skills": {"type": "multi_select"}}

        result = convert_openai_response_to_notion_update(openai_response, notion_properties)

        expected = {
            "properties": {
                "skills": {
                    "multi_select": [
                        {"name": "Python"},
                        {"name": "JavaScript"},
                        {"name": "Docker"},
                    ]
                }
            }
        }
        assert result == expected


class TestNotionPropertyToOpenAISchemaEnhanced:
    """Enhanced tests for notion_property_to_openai_schema function."""

    def test_property_with_description(self) -> None:
        """Test that descriptions are preserved in the schema."""
        notion_prop = {"type": "rich_text", "description": "A detailed description of this field"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        expected = {"type": "string", "maxLength": 2000, "description": "A detailed description of this field"}
        assert result == expected

    def test_select_with_empty_options_list(self) -> None:
        """Test select property with empty options list."""
        notion_prop = {"type": "select", "select": {"options": []}}
        result = notion_property_to_openai_schema(notion_prop, add_options=True)
        assert result == {"type": "string"}

    def test_multi_select_with_empty_options_list(self) -> None:
        """Test multi_select property with empty options list."""
        notion_prop = {"type": "multi_select", "multi_select": {"options": []}}
        result = notion_property_to_openai_schema(notion_prop, add_options=True)
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_status_with_empty_options_list(self) -> None:
        """Test status property with empty options list."""
        notion_prop = {"type": "status", "status": {"options": []}}
        result = notion_property_to_openai_schema(notion_prop, add_options=True)
        assert result == {"type": "string"}
