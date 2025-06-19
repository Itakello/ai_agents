"""Tests for the NotionPage model."""

from typing import Any

import pytest

from src.common.models.notion_page import (
    NotionCheckboxProperty,
    NotionDateProperty,
    NotionEmailProperty,
    NotionFilesProperty,
    NotionMultiSelectProperty,
    NotionNumberProperty,
    NotionPage,
    NotionPageProperties,
    NotionPhoneNumberProperty,
    NotionRichText,
    NotionRichTextProperty,
    NotionSelectProperty,
    NotionTitleProperty,
    NotionUrlProperty,
)


@pytest.fixture
def mock_rich_text() -> dict[str, Any]:
    """Create mock rich text data."""
    return {
        "type": "text",
        "text": {"content": "Test Text"},
        "annotations": {},
        "plain_text": "Test Text",
        "href": None,
    }


def test_notion_rich_text_creation(mock_rich_text: dict[str, Any]) -> None:
    """Test creating a NotionRichText instance."""
    rt = NotionRichText.model_validate(mock_rich_text)
    assert rt.type == "text"
    assert rt.text["content"] == "Test Text"
    assert rt.plain_text == "Test Text"


@pytest.fixture
def mock_page_data() -> dict[str, Any]:
    """Create mock page data for testing."""
    return {
        "object": "page",
        "id": "test-page-id",
        "title": [{"type": "text", "text": {"content": "Test Title"}, "plain_text": "Test Title"}],
        "created_time": "2024-01-01T00:00:00.000Z",
        "last_edited_time": "2024-01-01T00:00:00.000Z",
        "archived": False,
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
            "Number": {
                "id": "number",
                "type": "number",
                "name": "Number",
                "number": 42,
            },
            "Checkbox": {
                "id": "checkbox",
                "type": "checkbox",
                "name": "Checkbox",
                "checkbox": True,
            },
            "Select": {
                "id": "select",
                "type": "select",
                "name": "Select",
                "select": {"name": "Option 1"},
            },
            "MultiSelect": {
                "id": "multi_select",
                "type": "multi_select",
                "name": "MultiSelect",
                "multi_select": [{"name": "Option 1"}, {"name": "Option 2"}],
            },
            "URL": {
                "id": "url",
                "type": "url",
                "name": "URL",
                "url": "https://example.com",
            },
            "Email": {
                "id": "email",
                "type": "email",
                "name": "Email",
                "email": "test@example.com",
            },
            "Phone": {
                "id": "phone",
                "type": "phone_number",
                "name": "Phone",
                "phone_number": "+1234567890",
            },
            "Date": {
                "id": "date",
                "type": "date",
                "name": "Date",
                "date": {"start": "2024-01-01"},
            },
        },
    }


def test_notion_title_property() -> None:
    """Test creating a NotionTitleProperty instance."""
    data = {
        "type": "title",
        "id": "test-id",
        "name": "Title",
        "title": [
            {
                "type": "text",
                "text": {"content": "Test Title"},
                "plain_text": "Test Title",
            }
        ],
    }
    prop = NotionTitleProperty.model_validate(data)
    assert prop.type == "title"
    assert prop.id == "test-id"
    assert prop.name == "Title"
    assert len(prop.title) == 1
    assert prop.title[0].plain_text == "Test Title"


def test_notion_rich_text_property() -> None:
    """Test creating a NotionRichTextProperty instance."""
    data = {
        "type": "rich_text",
        "id": "test-id",
        "name": "Description",
        "rich_text": [
            {
                "type": "text",
                "text": {"content": "Test Description"},
                "plain_text": "Test Description",
            }
        ],
    }
    prop = NotionRichTextProperty.model_validate(data)
    assert prop.type == "rich_text"
    assert prop.id == "test-id"
    assert prop.name == "Description"
    assert len(prop.rich_text) == 1
    assert prop.rich_text[0].plain_text == "Test Description"


def test_notion_number_property() -> None:
    """Test creating a NotionNumberProperty instance."""
    data = {
        "type": "number",
        "id": "test-id",
        "name": "Count",
        "number": 42,
    }
    prop = NotionNumberProperty.model_validate(data)
    assert prop.type == "number"
    assert prop.id == "test-id"
    assert prop.name == "Count"
    assert prop.number == 42


def test_notion_checkbox_property() -> None:
    """Test creating a NotionCheckboxProperty instance."""
    data = {
        "type": "checkbox",
        "id": "test-id",
        "name": "Done",
        "checkbox": True,
    }
    prop = NotionCheckboxProperty.model_validate(data)
    assert prop.type == "checkbox"
    assert prop.id == "test-id"
    assert prop.name == "Done"
    assert prop.checkbox is True


def test_notion_select_property() -> None:
    """Test creating a NotionSelectProperty instance."""
    data = {
        "type": "select",
        "id": "test-id",
        "name": "Status",
        "select": {"name": "In Progress"},
    }
    prop = NotionSelectProperty.model_validate(data)
    assert prop.type == "select"
    assert prop.id == "test-id"
    assert prop.name == "Status"
    assert prop.select is not None
    assert prop.select["name"] == "In Progress"


def test_notion_multi_select_property() -> None:
    """Test creating a NotionMultiSelectProperty instance."""
    data = {
        "type": "multi_select",
        "id": "test-id",
        "name": "Tags",
        "multi_select": [{"name": "Tag1"}, {"name": "Tag2"}],
    }
    prop = NotionMultiSelectProperty.model_validate(data)
    assert prop.type == "multi_select"
    assert prop.id == "test-id"
    assert prop.name == "Tags"
    assert len(prop.multi_select) == 2
    assert prop.multi_select[0]["name"] == "Tag1"
    assert prop.multi_select[1]["name"] == "Tag2"


def test_notion_url_property() -> None:
    """Test creating a NotionUrlProperty instance."""
    data = {
        "type": "url",
        "id": "test-id",
        "name": "Website",
        "url": "https://example.com",
    }
    prop = NotionUrlProperty.model_validate(data)
    assert prop.type == "url"
    assert prop.id == "test-id"
    assert prop.name == "Website"
    assert prop.url == "https://example.com"


def test_notion_email_property() -> None:
    """Test creating a NotionEmailProperty instance."""
    data = {
        "type": "email",
        "id": "test-id",
        "name": "Email",
        "email": "test@example.com",
    }
    prop = NotionEmailProperty.model_validate(data)
    assert prop.type == "email"
    assert prop.id == "test-id"
    assert prop.name == "Email"
    assert prop.email == "test@example.com"


def test_notion_phone_number_property() -> None:
    """Test creating a NotionPhoneNumberProperty instance."""
    data = {
        "type": "phone_number",
        "id": "test-id",
        "name": "Phone",
        "phone_number": "+1234567890",
    }
    prop = NotionPhoneNumberProperty.model_validate(data)
    assert prop.type == "phone_number"
    assert prop.id == "test-id"
    assert prop.name == "Phone"
    assert prop.phone_number == "+1234567890"


def test_notion_date_property() -> None:
    """Test creating a NotionDateProperty instance."""
    data = {
        "type": "date",
        "id": "test-id",
        "name": "Due Date",
        "date": {"start": "2024-01-01"},
    }
    prop = NotionDateProperty.model_validate(data)
    assert prop.type == "date"
    assert prop.id == "test-id"
    assert prop.name == "Due Date"
    assert prop.date is not None
    assert prop.date["start"] == "2024-01-01"


def test_notion_files_property() -> None:
    """Test creating a NotionFilesProperty instance."""
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
    prop = NotionFilesProperty.model_validate(data)
    assert prop.type == "files"
    assert prop.id == "test-id"
    assert prop.name == "Attachments"
    assert len(prop.files) == 1
    assert prop.files[0]["name"] == "file1.pdf"


def test_notion_page_creation(mock_page_data: dict[str, Any]) -> None:
    """Test creating a NotionPage instance."""
    page = NotionPage.model_validate(mock_page_data)
    assert page.object == "page"
    assert page.id == "test-page-id"
    assert len(page.title) == 1
    assert page.title[0].plain_text == "Test Title"
    assert "Title" in page.properties.root
    assert "Company" in page.properties.root
    assert page.properties["Title"].type == "title"
    assert page.properties["Company"].type == "rich_text"
    assert page.properties["Number"].type == "number"
    assert page.properties["Checkbox"].type == "checkbox"
    assert page.properties["Select"].type == "select"
    assert page.properties["MultiSelect"].type == "multi_select"
    assert page.properties["URL"].type == "url"
    assert page.properties["Email"].type == "email"
    assert page.properties["Phone"].type == "phone_number"
    assert page.properties["Date"].type == "date"


def test_notion_page_empty_properties() -> None:
    """Test creating a NotionPage instance with no properties."""
    page = NotionPage(
        object="page",
        id="test-page-id",
        title=[NotionRichText(plain_text="Test Title", text={"content": "Test Title"})],
        properties=NotionPageProperties(root={}),
    )
    assert page.object == "page"
    assert page.id == "test-page-id"
    assert len(page.title) == 1
    assert page.title[0].plain_text == "Test Title"
    assert len(page.properties.root) == 0


def test_notion_page_format_properties(mock_page_data: dict[str, Any]) -> None:
    """Test formatting properties for Notion API."""
    page = NotionPage.model_validate(mock_page_data)
    properties = {
        "Title": "New Title",
        "Company": "New Company",
        "Number": 123,
        "Checkbox": True,
        "Select": "Option 3",
        "MultiSelect": ["Option 3", "Option 4"],
        "URL": "https://newexample.com",
        "Email": "new@example.com",
        "Phone": "+0987654321",
        "Date": "2024-02-01",
    }
    formatted = page.format_properties_for_notion(properties)
    assert isinstance(formatted, dict)
    assert "Title" in formatted
    assert "Company" in formatted
    assert formatted["Title"]["title"][0]["text"]["content"] == "New Title"
    assert formatted["Company"]["rich_text"][0]["text"]["content"] == "New Company"
    assert formatted["Number"]["number"] == 123
    assert formatted["Checkbox"]["checkbox"] is True
    assert formatted["Select"]["select"]["name"] == "Option 3"
    assert len(formatted["MultiSelect"]["multi_select"]) == 2
    assert formatted["URL"]["url"] == "https://newexample.com"
    assert formatted["Email"]["email"] == "new@example.com"
    assert formatted["Phone"]["phone_number"] == "+0987654321"
    assert formatted["Date"]["date"]["start"] == "2024-02-01"


def test_notion_page_format_properties_invalid_type(mock_page_data: dict[str, Any]) -> None:
    """Test formatting properties with invalid type."""
    page = NotionPage.model_validate(mock_page_data)
    properties = {
        "Title": 123,  # Invalid type for title
        "Number": "not a number",  # Invalid type for number
    }
    with pytest.raises(ValueError):
        page.format_properties_for_notion(properties)


def test_notion_page_format_properties_nonexistent(mock_page_data: dict[str, Any]) -> None:
    """Test formatting properties for non-existent property."""
    page = NotionPage.model_validate(mock_page_data)
    properties = {"NonexistentProperty": "value"}
    with pytest.raises(KeyError):
        page.format_properties_for_notion(properties)


def test_notion_page_format_properties_empty_values(mock_page_data: dict[str, Any]) -> None:
    """Test formatting properties with empty values."""
    page = NotionPage.model_validate(mock_page_data)
    properties: dict[str, Any] = {
        "Title": "",
        "Company": "",
        "Number": None,
        "Checkbox": False,
        "Select": None,
        "MultiSelect": [],
        "URL": "",
        "Email": "",
        "Phone": "",
        "Date": None,
    }
    formatted = page.format_properties_for_notion(properties)
    assert formatted["Title"]["title"][0]["text"]["content"] == ""
    assert formatted["Company"]["rich_text"][0]["text"]["content"] == ""
    assert formatted["Number"]["number"] is None
    assert formatted["Checkbox"]["checkbox"] is False
    assert formatted["Select"]["select"] is None
    assert formatted["MultiSelect"]["multi_select"] == []
    assert formatted["URL"]["url"] is None
    assert formatted["Email"]["email"] is None
    assert formatted["Phone"]["phone_number"] is None
    assert formatted["Date"]["date"] is None
