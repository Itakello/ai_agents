from collections.abc import ItemsView, KeysView, ValuesView
from typing import Any, Literal

from pydantic import BaseModel, Field, RootModel


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


class NotionPageProperties(RootModel[dict[str, "NotionPropertyItem"]]):
    """Represents the 'properties' field of a Notion page object."""

    # Using a dictionary where keys are property names and values are NotionPropertyItem
    # This allows dynamic property names.
    # For more type safety on known properties, they could be explicit fields.
    # Example: 'Name': NotionPropertyItem, 'Date Created': NotionPropertyItem
    # However, property names are dynamic, so dict is more flexible.

    def __getitem__(self, item: str) -> "NotionPropertyItem":
        return self.root[item]

    def get(self, item: str, default: Any | None = None) -> "NotionPropertyItem | None":
        return self.root.get(item, default)

    def items(self) -> ItemsView[str, "NotionPropertyItem"]:
        return self.root.items()

    def keys(self) -> KeysView[str]:
        return self.root.keys()

    def values(self) -> ValuesView["NotionPropertyItem"]:
        return self.root.values()


class NotionPage(BaseModel):
    """Representation of a Notion Page with convenience helpers."""

    object: Literal["page"] = Field(description="Object type, always 'page'.")
    id: str = Field(description="Page ID.")

    # Timestamps
    created_time: str
    last_edited_time: str

    # Archive / trash flags -------------------------------------------------
    archived: bool | None = None
    in_trash: bool | None = None

    # Parent information (database_id, page_id or workspace) --------------
    parent: dict[str, Any] | None = None

    # Visuals --------------------------------------------------------------
    icon: dict[str, Any] | None = None
    cover: dict[str, Any] | None = None

    # URL ------------------------------------------------------------------
    url: str | None = None
    public_url: str | None = None

    # The actual content of interest
    properties: NotionPageProperties = Field(description="Page properties.")

    def title_text(self) -> str | None:
        """Extract the title text from the page properties."""
        for prop in self.properties.values():
            if prop.type == "title" and prop.title:
                return "".join(rt.plain_text for rt in prop.title)
        return None

    class Config:
        extra = "allow"


class NotionDatabaseSchemaProperty(BaseModel):
    """Represents the configuration of a single property in a Notion database schema."""

    id: str
    name: str
    type: str  # e.g. "title", "rich_text", "select", ...
    description: str | None = None

    # Type-specific configuration
    select: dict[str, Any] | None = None
    multi_select: dict[str, Any] | None = None
    title: list[NotionRichText] | None = None
    status: dict[str, Any] | None = None

    # Fallback for any additional, not yet modelled configuration blocks
    other_config: dict[str, Any] | None = Field(
        default=None,
        description="Catch-all for configuration keys not explicitly modelled above.",
    )

    class Config:
        extra = "allow"  # tolerate new/unknown fields returned by Notion


class NotionDatabase(BaseModel):
    """Representation of a Notion Database with helpers."""

    object: Literal["database"] = Field(description="Object type, always 'database'.")
    id: str
    title: list[NotionRichText]
    description: list[NotionRichText] | None = None
    properties: dict[str, NotionDatabaseSchemaProperty]

    # Parent information and misc flags
    parent: dict[str, Any] | None = None
    url: str | None = None
    archived: bool | None = None
    is_inline: bool | None = None
    in_trash: bool | None = None
    public_url: str | None = None

    # Convenience helpers
    def get_schema(self) -> dict[str, "NotionDatabaseSchemaProperty"]:
        """Return the database property schema (alias for ``self.properties``)."""
        return self.properties

    def get_property(self, name: str) -> "NotionDatabaseSchemaProperty":
        """Return a property value by name."""
        return self.properties[name]

    def title_text(self) -> str | None:
        """Return plain-text title if a `Title` property exists."""
        title_prop = self.properties.get("Title")
        if title_prop and title_prop.title:
            return "".join(rt.plain_text for rt in title_prop.title)
        return None

    class Config:
        extra = "allow"
