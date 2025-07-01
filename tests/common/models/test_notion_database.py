"""Tests for the NotionDatabase model."""

from typing import Any

import pytest

from src.common.models.notion_database import (
    NotionDatabase,
    NotionDatabaseCheckboxProperty,
    NotionDatabaseDateProperty,
    NotionDatabaseEmailProperty,
    NotionDatabaseFilesProperty,
    NotionDatabaseMultiSelectProperty,
    NotionDatabaseNumberProperty,
    NotionDatabasePhoneNumberProperty,
    NotionDatabaseRichTextProperty,
    NotionDatabaseSelectProperty,
    NotionDatabaseTitleProperty,
    NotionDatabaseUrlProperty,
    NotionRichText,
)


@pytest.fixture
def mock_database_data() -> dict[str, Any]:
    """Create mock database data for testing."""
    return {
        "id": "test-db-id",
        "object": "database",
        "title": [{"type": "text", "text": {"content": "Test Database"}, "plain_text": "Test Database"}],
        "properties": {
            "Title": {
                "id": "title",
                "type": "title",
                "name": "Title",
                "title": [{"type": "text", "text": {"content": "Test Title"}, "plain_text": "Test Title"}],
            },
            "Company": {
                "id": "company",
                "type": "rich_text",
                "name": "Company",
                "rich_text": [{"type": "text", "text": {"content": "Test Company"}, "plain_text": "Test Company"}],
            },
        },
    }


def test_notion_database_title_property() -> None:
    """Test creating a NotionDatabaseTitleProperty instance."""
    data = {
        "type": "title",
        "id": "test-id",
        "name": "Title",
        "title": [{"type": "text", "text": {"content": "Test Title"}, "plain_text": "Test Title"}],
    }
    prop = NotionDatabaseTitleProperty.model_validate(data)
    assert prop.type == "title"
    assert prop.id == "test-id"
    assert prop.name == "Title"
    assert prop.title is not None
    assert len(prop.title) == 1
    assert prop.title[0].plain_text == "Test Title"


def test_notion_database_rich_text_property() -> None:
    """Test creating a NotionDatabaseRichTextProperty instance."""
    data = {
        "type": "rich_text",
        "id": "test-id",
        "name": "Description",
        "rich_text": [{"type": "text", "text": {"content": "Test Description"}, "plain_text": "Test Description"}],
    }
    prop = NotionDatabaseRichTextProperty.model_validate(data)
    assert prop.type == "rich_text"
    assert prop.id == "test-id"
    assert prop.name == "Description"
    assert prop.rich_text is not None
    assert len(prop.rich_text) == 1
    assert prop.rich_text[0].plain_text == "Test Description"


def test_notion_database_number_property() -> None:
    """Test creating a NotionDatabaseNumberProperty instance."""
    data = {
        "type": "number",
        "id": "test-id",
        "name": "Count",
        "number": 42,
    }
    prop = NotionDatabaseNumberProperty.model_validate(data)
    assert prop.type == "number"
    assert prop.id == "test-id"
    assert prop.name == "Count"
    assert prop.number == 42


def test_notion_database_checkbox_property() -> None:
    """Test creating a NotionDatabaseCheckboxProperty instance."""
    data = {
        "type": "checkbox",
        "id": "test-id",
        "name": "Done",
        "checkbox": True,
    }
    prop = NotionDatabaseCheckboxProperty.model_validate(data)
    assert prop.type == "checkbox"
    assert prop.id == "test-id"
    assert prop.name == "Done"
    assert prop.checkbox is True


def test_notion_database_select_property() -> None:
    """Test creating a NotionDatabaseSelectProperty instance."""
    data = {
        "type": "select",
        "id": "test-id",
        "name": "Status",
        "select": {"name": "In Progress"},
    }
    prop = NotionDatabaseSelectProperty.model_validate(data)
    assert prop.type == "select"
    assert prop.id == "test-id"
    assert prop.name == "Status"
    assert prop.select is not None
    assert prop.select["name"] == "In Progress"


def test_notion_database_multi_select_property() -> None:
    """Test creating a NotionDatabaseMultiSelectProperty instance."""
    data = {
        "type": "multi_select",
        "id": "test-id",
        "name": "Tags",
        "multi_select": {"options": [{"name": "Tag1"}, {"name": "Tag2"}]},
    }
    prop = NotionDatabaseMultiSelectProperty.model_validate(data)
    assert prop.type == "multi_select"
    assert prop.id == "test-id"
    assert prop.name == "Tags"
    assert prop.multi_select is not None
    assert "options" in prop.multi_select
    assert len(prop.multi_select["options"]) == 2
    assert prop.multi_select["options"][0]["name"] == "Tag1"
    assert prop.multi_select["options"][1]["name"] == "Tag2"


def test_notion_database_url_property() -> None:
    """Test creating a NotionDatabaseUrlProperty instance."""
    data = {
        "type": "url",
        "id": "test-id",
        "name": "Website",
        "url": "https://example.com",
    }
    prop = NotionDatabaseUrlProperty.model_validate(data)
    assert prop.type == "url"
    assert prop.id == "test-id"
    assert prop.name == "Website"
    assert prop.url == "https://example.com"


def test_notion_database_email_property() -> None:
    """Test creating a NotionDatabaseEmailProperty instance."""
    data = {
        "type": "email",
        "id": "test-id",
        "name": "Email",
        "email": "test@example.com",
    }
    prop = NotionDatabaseEmailProperty.model_validate(data)
    assert prop.type == "email"
    assert prop.id == "test-id"
    assert prop.name == "Email"
    assert prop.email == "test@example.com"


def test_notion_database_phone_number_property() -> None:
    """Test creating a NotionDatabasePhoneNumberProperty instance."""
    data = {
        "type": "phone_number",
        "id": "test-id",
        "name": "Phone",
        "phone_number": "+1234567890",
    }
    prop = NotionDatabasePhoneNumberProperty.model_validate(data)
    assert prop.type == "phone_number"
    assert prop.id == "test-id"
    assert prop.name == "Phone"
    assert prop.phone_number == "+1234567890"


def test_notion_database_date_property() -> None:
    """Test creating a NotionDatabaseDateProperty instance."""
    data = {
        "type": "date",
        "id": "test-id",
        "name": "Due Date",
        "date": {"start": "2024-01-01"},
    }
    prop = NotionDatabaseDateProperty.model_validate(data)
    assert prop.type == "date"
    assert prop.id == "test-id"
    assert prop.name == "Due Date"
    assert prop.date is not None
    assert prop.date["start"] == "2024-01-01"


def test_notion_database_files_property() -> None:
    """Test creating a NotionDatabaseFilesProperty instance."""
    data = {
        "type": "files",
        "id": "test-id",
        "name": "Attachments",
        "files": [
            {
                "type": "file",
                "file": {"url": "https://example.com/file1.pdf"},
                "name": "file1.pdf",
            }
        ],
    }
    prop = NotionDatabaseFilesProperty.model_validate(data)
    assert prop.type == "files"
    assert prop.id == "test-id"
    assert prop.name == "Attachments"
    assert prop.files is not None
    assert len(prop.files) == 1
    assert prop.files[0]["name"] == "file1.pdf"


def test_notion_database_creation() -> None:
    """Test creating a Notion database with properties"""
    # Create a database with some properties
    db = NotionDatabase(
        id="test-db-id",
        object="database",
        title=[NotionRichText(plain_text="Test Database", type="text", text={"content": "Test Database"})],
        properties={
            "Name": NotionDatabaseTitleProperty(id="title", name="Name"),
            "Description": NotionDatabaseRichTextProperty(id="rich_text", name="Description"),
        },
    )

    # Verify database properties
    assert db.id == "test-db-id"
    assert len(db.title) == 1
    assert db.title[0].plain_text == "Test Database"
    assert "Name" in db.properties
    assert "Description" in db.properties
    assert db.properties["Name"].type == "title"
    assert db.properties["Description"].type == "rich_text"


def test_notion_database_empty_properties() -> None:
    """Test creating a Notion database with no properties"""
    db = NotionDatabase(
        id="test-db-id",
        object="database",
        title=[NotionRichText(plain_text="Test Database", text={"content": "Test Database"})],
        properties={},
    )

    assert db.id == "test-db-id"
    assert len(db.title) == 1
    assert db.title[0].plain_text == "Test Database"
    assert len(db.properties) == 0


def test_notion_database_schema_verification() -> None:
    """Test database schema verification"""
    db = NotionDatabase(
        id="test-db-id",
        object="database",
        title=[NotionRichText(plain_text="Test Database", text={"content": "Test Database"})],
        properties={
            "Name": NotionDatabaseTitleProperty(id="title", name="Name"),
            "Description": NotionDatabaseRichTextProperty(id="rich_text", name="Description"),
        },
    )

    required_props = {"Name": "title", "Description": "rich_text"}
    missing_or_incorrect = db.verify_schema(required_props)
    assert len(missing_or_incorrect) == 0

    required_props = {"Name": "title", "Description": "rich_text", "Status": "select"}
    missing_or_incorrect = db.verify_schema(required_props)
    assert "Status" in missing_or_incorrect
    assert len(missing_or_incorrect) == 1

    required_props = {
        "Name": "title",
        "Description": "select",
    }
    missing_or_incorrect = db.verify_schema(required_props)
    assert "Description" in missing_or_incorrect
    assert len(missing_or_incorrect) == 1


def test_notion_database_schema_fix() -> None:
    """Test database schema fixing"""
    db = NotionDatabase(
        id="test-db-id",
        object="database",
        title=[NotionRichText(plain_text="Test Database", text={"content": "Test Database"})],
        properties={
            "Name": NotionDatabaseTitleProperty(id="title", name="Name"),
            "Description": NotionDatabaseRichTextProperty(id="rich_text", name="Description"),
        },
    )

    required_props = {
        "Name": "title",
        "Description": "select",
        "Status": "select",
    }
    db.fix_schema(required_props)

    assert "Status" in db.properties
    assert db.properties["Status"].type == "select"
    assert db.properties["Description"].type == "select"
    assert db.properties["Name"].type == "title"
