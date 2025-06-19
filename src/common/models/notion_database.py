"""Notion Database model with enhanced functionality."""

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from .notion_page import NotionRichText

T = TypeVar(
    "T",
    bound=Literal[
        "title",
        "rich_text",
        "number",
        "checkbox",
        "select",
        "multi_select",
        "url",
        "email",
        "phone_number",
        "date",
        "files",
        "status",
        "created_time",
        "last_edited_time",
    ],
)


class NotionDatabaseProperty(BaseModel, Generic[T]):
    """Base class for Notion database properties."""

    id: str
    type: T
    name: str
    description: str | None = None

    # Allow unknown keys (e.g. 'select', 'multi_select', 'status', etc.) to be stored and
    # included in serialisation so that downstream utilities can still access the raw
    # Notion schema information (options lists, configuration, …).
    model_config = {
        "extra": "allow",
    }


class NotionDatabaseTitleProperty(NotionDatabaseProperty[Literal["title"]]):
    """Notion database title property."""

    type: Literal["title"] = "title"
    title: list[NotionRichText] | None = None


class NotionDatabaseRichTextProperty(NotionDatabaseProperty[Literal["rich_text"]]):
    """Notion database rich text property."""

    type: Literal["rich_text"] = "rich_text"
    rich_text: list[NotionRichText] | None = None


class NotionDatabaseNumberProperty(NotionDatabaseProperty[Literal["number"]]):
    """Notion database number property."""

    type: Literal["number"] = "number"
    number: float | None = None


class NotionDatabaseCheckboxProperty(NotionDatabaseProperty[Literal["checkbox"]]):
    """Notion database checkbox property."""

    type: Literal["checkbox"] = "checkbox"
    checkbox: bool | None = None


class NotionDatabaseSelectProperty(NotionDatabaseProperty[Literal["select"]]):
    """Notion database select property."""

    type: Literal["select"] = "select"
    select: dict[str, Any] | None = None


class NotionDatabaseMultiSelectProperty(NotionDatabaseProperty[Literal["multi_select"]]):
    """Notion database multi-select property."""

    type: Literal["multi_select"] = "multi_select"
    multi_select: dict[str, Any] | None = None


class NotionDatabaseUrlProperty(NotionDatabaseProperty[Literal["url"]]):
    """Notion database URL property."""

    type: Literal["url"] = "url"
    url: str | None = None


class NotionDatabaseEmailProperty(NotionDatabaseProperty[Literal["email"]]):
    """Notion database email property."""

    type: Literal["email"] = "email"
    email: str | None = None


class NotionDatabasePhoneNumberProperty(NotionDatabaseProperty[Literal["phone_number"]]):
    """Notion database phone number property."""

    type: Literal["phone_number"] = "phone_number"
    phone_number: str | None = None


class NotionDatabaseDateProperty(NotionDatabaseProperty[Literal["date"]]):
    """Notion database date property."""

    type: Literal["date"] = "date"
    date: dict[str, str] | None = None


class NotionDatabaseFilesProperty(NotionDatabaseProperty[Literal["files"]]):
    """Notion database files property."""

    type: Literal["files"] = "files"
    files: list[dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Additional property types (status / timestamps)
# ---------------------------------------------------------------------------


class NotionDatabaseStatusProperty(NotionDatabaseProperty[Literal["status"]]):
    """Notion database status property."""

    type: Literal["status"] = "status"
    status: dict[str, Any] | None = None


class NotionDatabaseCreatedTimeProperty(NotionDatabaseProperty[Literal["created_time"]]):
    """Read-only timestamp when the page was created."""

    type: Literal["created_time"] = "created_time"
    created_time: str | None = None


class NotionDatabaseLastEditedTimeProperty(NotionDatabaseProperty[Literal["last_edited_time"]]):
    """Read-only timestamp when the page was last edited."""

    type: Literal["last_edited_time"] = "last_edited_time"
    last_edited_time: str | None = None


class NotionDatabase(BaseModel):
    """Representation of a Notion Database with enhanced functionality."""

    object: Literal["database"] = Field(description="Object type, always 'database'.")
    id: str
    title: list[NotionRichText] = Field(description="Database title.")
    properties: dict[str, NotionDatabaseProperty]
    description: list[NotionRichText] | None = None

    def get_schema(self) -> dict[str, str]:
        """Get the database schema as a dictionary of property names to types"""
        return {name: prop.type for name, prop in self.properties.items()}

    def get_property(self, name: str) -> NotionDatabaseProperty | None:
        """Get a property by name"""
        return self.properties.get(name)

    def verify_schema(self, required_properties: dict[str, str]) -> set[str]:
        """Verify that the database has all required properties with correct types"""
        missing_or_incorrect = set()

        for prop_name, expected_type in required_properties.items():
            if prop_name not in self.properties:
                missing_or_incorrect.add(prop_name)
            elif str(self.properties[prop_name].type) != expected_type:
                missing_or_incorrect.add(prop_name)

        return missing_or_incorrect

    def fix_schema(self, required_properties: dict[str, str]) -> None:
        """Fix the database schema by adding missing properties and correcting types"""
        missing_or_incorrect = self.verify_schema(required_properties)

        for prop_name in missing_or_incorrect:
            self.properties[prop_name] = self._create_property(prop_name, required_properties[prop_name])

    def _create_property(self, name: str, type_name: str) -> NotionDatabaseProperty:
        """Create a property of the specified type"""
        property_classes = {
            "title": NotionDatabaseTitleProperty,
            "rich_text": NotionDatabaseRichTextProperty,
            "number": NotionDatabaseNumberProperty,
            "checkbox": NotionDatabaseCheckboxProperty,
            "select": NotionDatabaseSelectProperty,
            "multi_select": NotionDatabaseMultiSelectProperty,
            "url": NotionDatabaseUrlProperty,
            "email": NotionDatabaseEmailProperty,
            "phone_number": NotionDatabasePhoneNumberProperty,
            "date": NotionDatabaseDateProperty,
            "files": NotionDatabaseFilesProperty,
            "status": NotionDatabaseStatusProperty,
            "created_time": NotionDatabaseCreatedTimeProperty,
            "last_edited_time": NotionDatabaseLastEditedTimeProperty,
        }

        if type_name not in property_classes:
            raise ValueError(f"Unknown property type: {type_name}")

        return property_classes[type_name](id=f"prop_{name}", type=type_name, name=name)  # type: ignore
