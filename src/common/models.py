from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import ItemsView, KeysView, ValuesView

from pydantic import BaseModel, Field


class NotionFileObject(BaseModel):
    """Represents a file object within a Notion 'files' property."""

    name: str | None = Field(default=None, description="Name of the file as it appears in Notion.")
    type: Literal["file", "external"] | None = Field(default=None, description="Type of the file link.")
    url: str = Field(description="URL of the file.")

    # Nested structures for 'file' and 'external' types
    # These are simplified; Notion API has more details like expiry_time for 'file'
    file: dict[str, Any] | None = Field(default=None, description="Internal Notion file details.")
    external: dict[str, Any] | None = Field(default=None, description="External file link details.")


class NotionRichText(BaseModel):
    """Represents a rich text object in Notion."""

    type: Literal["text", "mention", "equation"] = Field(description="Type of rich text component.")
    plain_text: str = Field(description="The plain text content.")
    href: str | None = Field(default=None, description="URL if the text is a link.")
    # Annotations and other type-specific fields (text, mention, equation) can be added here
    annotations: dict[str, Any] | None = Field(default=None, description="Styling annotations.")
    text: dict[str, Any] | None = Field(default=None, description="Text content details.")
    mention: dict[str, Any] | None = Field(default=None, description="Mention details.")
    equation: dict[str, Any] | None = Field(default=None, description="Equation details.")


class NotionPropertyItem(BaseModel):
    """Represents a generic Notion property value as retrieved from a page.
    This is a base and might need to be a discriminated union for full type safety.
    """

    id: str = Field(description="ID of the property.")
    type: str = Field(description="Type of the Notion property (e.g., 'rich_text', 'files', 'select').")

    # Type-specific fields - use Any for now, can be refined with Union types
    rich_text: list[NotionRichText] | None = Field(default=None)
    files: list[NotionFileObject] | None = Field(default=None)
    title: list[NotionRichText] | None = Field(default=None)
    select: dict[str, Any] | None = Field(default=None)  # Corresponds to NotionSelectOptionData
    multi_select: list[dict[str, Any]] | None = Field(default=None)  # List of NotionSelectOptionData
    status: dict[str, Any] | None = Field(default=None)  # Corresponds to NotionSelectOptionData
    date: dict[str, Any] | None = Field(default=None)
    number: float | int | None = Field(default=None)
    checkbox: bool | None = Field(default=None)
    url: str | None = Field(default=None)
    email: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)
    formula: dict[str, Any] | None = Field(default=None)
    relation: list[dict[str, Any]] | None = Field(default=None)
    rollup: dict[str, Any] | None = Field(default=None)
    created_time: str | None = Field(default=None)
    created_by: dict[str, Any] | None = Field(default=None)
    last_edited_time: str | None = Field(default=None)
    last_edited_by: dict[str, Any] | None = Field(default=None)

    # Catch-all for other property types not explicitly defined
    # extra_data: dict[str, Any] = Field(default_factory=dict, alias_for_extra=True)

    class Config:
        extra = "allow"  # Allow other property types not explicitly defined


class NotionPageProperties(BaseModel):
    """Represents the 'properties' field of a Notion page object."""

    # Using a dictionary where keys are property names and values are NotionPropertyItem
    # This allows dynamic property names.
    # For more type safety on known properties, they could be explicit fields.
    # Example: 'Name': NotionPropertyItem, 'Date Created': NotionPropertyItem
    # However, property names are dynamic, so dict is more flexible.
    __root__: dict[str, NotionPropertyItem]

    def __getitem__(self, item: str) -> NotionPropertyItem:
        return self.__root__[item]

    def get(self, item: str, default: Any | None = None) -> NotionPropertyItem | Any | None:
        return self.__root__.get(item, default)

    def items(self) -> ItemsView[str, NotionPropertyItem]:
        return self.__root__.items()

    def keys(self) -> KeysView[str]:
        return self.__root__.keys()

    def values(self) -> ValuesView[NotionPropertyItem]:
        return self.__root__.values()


class NotionPage(BaseModel):
    """Simplified representation of a Notion Page object."""

    object: Literal["page"] = Field(description="Object type, always 'page'.")
    id: str = Field(description="Page ID.")
    created_time: str
    last_edited_time: str
    archived: bool
    parent: dict[str, Any]  # Could be DatabaseParent, PageParent, WorkspaceParent
    url: str
    properties: NotionPageProperties = Field(description="Page properties.")
    # icon, cover, created_by, last_edited_by can be added as needed


class NotionDatabaseSchemaProperty(BaseModel):
    """Represents the configuration of a single property in a Notion database schema."""

    id: str
    name: str
    type: str
    description: str | None = None
    # Type-specific configuration (e.g., options for select, formula for formula)
    # This is simplified; each type (select, multi_select, status, etc.) has its own object structure.
    # Consider using a discriminated union based on 'type' for full modeling.
    select: dict[str, Any] | None = None
    multi_select: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
    # ... other property type configurations

    class Config:
        extra = "allow"  # Allow other property-specific config fields


class NotionDatabase(BaseModel):
    """Simplified representation of a Notion Database object."""

    object: Literal["database"] = Field(description="Object type, always 'database'.")
    id: str
    created_time: str
    last_edited_time: str
    title: list[NotionRichText]
    description: list[NotionRichText]
    properties: dict[str, NotionDatabaseSchemaProperty]
    parent: dict[str, Any]
    url: str
    archived: bool
    is_inline: bool
    # icon, cover, created_by, last_edited_by can be added as needed
