"""Notion Page model with enhanced functionality."""

from collections.abc import ItemsView, KeysView, ValuesView
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, RootModel


class NotionRichText(BaseModel):
    """Representation of Notion rich text returned by the Notion API.

    The official API returns a fairly flexible payload.  To avoid extremely
    brittle validation errors we purposefully **relax** some of the strict
    typing that was previously in place:

    • ``text`` can contain keys whose values might be ``None`` (e.g.
      ``{"content": "Foo", "link": None}``).  We therefore allow *any*
      JSON-serialisable values.

    • ``annotations`` include the usual boolean styling flags **and** a
      ``color`` field that is a string (``"default"`` by default).  A simple
      ``dict[str, Any]`` covers this.
    """

    type: Literal["text"] = "text"
    text: dict[str, Any]
    annotations: dict[str, Any] = Field(default_factory=dict)
    plain_text: str
    href: str | None = None


T = TypeVar("T", bound=str)


class NotionPageProperty(BaseModel, Generic[T]):
    """Base class for Notion page properties.

    The Notion API embeds the *property name* as the key in the surrounding
    JSON object – it is **not** repeated inside the value object.  Therefore
    the ``name`` attribute that existed previously caused validation errors
    and has been removed.
    """

    id: str
    type: T
    # *Page* property objects do not include the name inside the JSON payload
    # (it's the outer dict key) – however keeping the attribute **optional**
    # preserves backwards-compatibility with existing unit-tests that expect
    # it to be there when provided by fixtures.
    name: str | None = None

    # Keep any additional keys found in the value object (for example 'multi_select', 'select', …)
    model_config = {
        "extra": "allow",
    }


class NotionTitleProperty(NotionPageProperty[Literal["title"]]):
    """Notion title property."""

    type: Literal["title"] = "title"
    title: list[NotionRichText]


class NotionRichTextProperty(NotionPageProperty[Literal["rich_text"]]):
    """Notion rich text property."""

    type: Literal["rich_text"] = "rich_text"
    rich_text: list[NotionRichText]


class NotionNumberProperty(NotionPageProperty[Literal["number"]]):
    """Notion number property."""

    type: Literal["number"] = "number"
    number: float | None


class NotionCheckboxProperty(NotionPageProperty[Literal["checkbox"]]):
    """Notion checkbox property."""

    type: Literal["checkbox"] = "checkbox"
    checkbox: bool


class NotionSelectProperty(NotionPageProperty[Literal["select"]]):
    """Notion select property."""

    type: Literal["select"] = "select"
    select: dict[str, str] | None


class NotionMultiSelectProperty(NotionPageProperty[Literal["multi_select"]]):
    """Notion multi-select property."""

    type: Literal["multi_select"] = "multi_select"
    multi_select: list[dict[str, str]]


class NotionUrlProperty(NotionPageProperty[Literal["url"]]):
    """Notion URL property."""

    type: Literal["url"] = "url"
    url: str | None


class NotionEmailProperty(NotionPageProperty[Literal["email"]]):
    """Notion email property."""

    type: Literal["email"] = "email"
    email: str | None


class NotionPhoneNumberProperty(NotionPageProperty[Literal["phone_number"]]):
    """Notion phone number property."""

    type: Literal["phone_number"] = "phone_number"
    phone_number: str | None


class NotionDateProperty(NotionPageProperty[Literal["date"]]):
    """Notion date property."""

    type: Literal["date"] = "date"
    date: dict[str, str] | None


class NotionFilesProperty(NotionPageProperty[Literal["files"]]):
    """Notion files property."""

    type: Literal["files"] = "files"
    files: list[dict[str, Any]]


class NotionPageProperties(RootModel[dict[str, NotionPageProperty]]):
    """Represents the 'properties' field of a Notion page object."""

    def __getitem__(self, item: str) -> NotionPageProperty:
        return self.root[item]

    def get(self, item: str, default: Any | None = None) -> NotionPageProperty | None:
        return self.root.get(item, default)

    def items(self) -> ItemsView[str, NotionPageProperty]:
        return self.root.items()

    def keys(self) -> KeysView[str]:
        return self.root.keys()

    def values(self) -> ValuesView[NotionPageProperty]:
        return self.root.values()


class NotionPage(BaseModel):
    """Representation of a Notion Page with enhanced functionality."""

    object: Literal["page"] = Field(description="Object type, always 'page'.")
    id: str = Field(description="Page ID.")
    # Notion API may omit the ``title`` field altogether for results coming from
    # database queries.  For the rest of the codebase (and especially the unit-
    # tests) it is far more convenient to always handle *a list* – an empty
    # list when the title is missing mimics the payload shape Notion uses even
    # when there is no content.
    title: list[NotionRichText] = Field(default_factory=list, description="Page title (may be empty).")
    properties: NotionPageProperties = Field(description="Page properties.")

    def format_properties_for_notion(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Format properties for Notion API update.

        Args:
            properties: Dictionary of property names to values.

        Returns:
            Dictionary formatted for Notion API update.

        Raises:
            KeyError: If a property doesn't exist in the page.
            ValueError: If a property value is invalid for its type.
        """
        formatted: dict[str, Any] = {}

        for prop_name, value in properties.items():
            if prop_name not in self.properties.root:
                raise KeyError(f"Property {prop_name} does not exist in page")

            prop = self.properties.root[prop_name]
            prop_type = prop.type

            match prop_type:
                case "title" | "rich_text":
                    if not isinstance(value, str):
                        raise ValueError(f"Property {prop_name} must be a string")
                    formatted[prop_name] = {prop_type: [{"type": "text", "text": {"content": value}}]}
                case "number":
                    if not isinstance(value, (int | float)) and value is not None:
                        raise ValueError(f"Property {prop_name} must be a number")
                    formatted[prop_name] = {"number": value}
                case "checkbox":
                    if not isinstance(value, bool):
                        raise ValueError(f"Property {prop_name} must be a boolean")
                    formatted[prop_name] = {"checkbox": value}
                case "select":
                    if value is not None and not isinstance(value, str):
                        raise ValueError(f"Property {prop_name} must be a string")
                    formatted[prop_name] = {"select": {"name": value} if value else None}
                case "multi_select":
                    if not isinstance(value, list):
                        raise ValueError(f"Property {prop_name} must be a list")
                    formatted[prop_name] = {"multi_select": [{"name": str(v)} for v in value if v is not None]}
                case "url" | "email" | "phone_number":
                    if value is not None and not isinstance(value, str):
                        raise ValueError(f"Property {prop_name} must be a string")
                    formatted[prop_name] = {prop_type: value if value else None}
                case "date":
                    if value is not None and not isinstance(value, str):
                        raise ValueError(f"Property {prop_name} must be a string")
                    formatted[prop_name] = {"date": {"start": value} if value else None}
                case _:
                    raise ValueError(f"Unsupported property type: {prop_type}")

        return formatted
