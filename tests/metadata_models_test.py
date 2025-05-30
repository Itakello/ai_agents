"""Tests for metadata extraction models and conversion functions."""

from src.metadata_extraction.models import (
    convert_openai_response_to_notion_update,
    create_openai_schema_from_notion_database,
    notion_property_to_openai_schema,
    openai_data_to_notion_property,
)


class TestNotionPropertyToOpenAISchema:
    """Test conversion from Notion property definitions to OpenAI JSON Schema."""

    def test_rich_text_property(self) -> None:
        notion_prop = {"type": "rich_text"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string"}

    def test_title_property(self) -> None:
        notion_prop = {"type": "title"}
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
        assert result == {"type": "string"}

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
        result = notion_property_to_openai_schema(notion_prop, add_options=False)
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
        assert result == {"rich_text": [{"text": {"content": "Hello World"}}]}

    def test_title_conversion(self) -> None:
        result = openai_data_to_notion_property("Job Title", "title")
        assert result == {"rich_text": [{"text": {"content": "Job Title"}}]}

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
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False)

        expected = {
            "type": "object",
            "properties": {
                "job_title": {"type": "string"},
                "company": {"type": "string"},
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
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False)

        # Only job_title should be included
        expected = {
            "type": "object",
            "properties": {"job_title": {"type": "string"}},
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
        result = create_openai_schema_from_notion_database(notion_properties, add_options=False)

        expected = {
            "type": "object",
            "properties": {"experience_level": {"type": "string", "enum": ["Junior", "Mid", "Senior"]}},
            "required": ["experience_level"],
            "additionalProperties": False,
        }
        assert result == expected


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
                "job_title": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
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
            "properties": {
                "job_title": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
            }
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
            "properties": {
                "job_title": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
            }
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
