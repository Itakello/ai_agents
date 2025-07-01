from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NotionSelectOption(BaseModel):
    """Represents an option in a Notion 'select', 'multi_select', or 'status' property schema."""

    id: str | None = Field(default=None, description="ID of the option.")
    name: str = Field(description="Name of the option.")
    color: str | None = Field(default=None, description="Color of the option.")
    description: str | None = Field(default=None, description="Description of the option, for status type.")


class NotionPropertySchemaTypeDetails(BaseModel):
    """Holds the type-specific configuration for a Notion property schema.
    Example: for a 'select' property, this would contain 'options'.
    This is a flexible container; for full type safety, use discriminated unions.
    """

    options: list[NotionSelectOption] | None = Field(
        default=None, description="Options for select, multi_select, or status properties."
    )
    # Add other type-specific fields here, e.g.:
    # formula: dict[str, Any] | None = Field(default=None, description="Formula details for formula properties.")
    # relation_database_id: str | None = Field(default=None, description="Database ID for relation properties.")
    # rollup: dict[str, Any] | None = Field(default=None, description="Rollup configuration.")

    class Config:
        extra = "allow"  # Allow other type-specific fields


class NotionPropertySchema(BaseModel):
    """Represents the schema of a single property in a Notion database.
    This is used as input/output when converting to/from OpenAI schemas.
    """

    id: str = Field(description="ID of the property.")
    name: str = Field(description="Name of the property.")
    type: str = Field(description="Type of the Notion property (e.g., 'select', 'text', 'date').")
    description: str | None = Field(default=None, description="Description of the property.")

    # Type-specific configurations are nested under a key matching the 'type' value
    # e.g., if type is 'select', there will be a 'select' field with options.
    # Using a generic dict here for flexibility, can be made specific with Unions.
    # Example: select: NotionPropertySchemaTypeDetails | None
    #          multi_select: NotionPropertySchemaTypeDetails | None
    #          status: NotionPropertySchemaTypeDetails | None
    # For now, we allow any extra fields to capture these type-specific details.
    # The actual structure is notion_db.properties.property_name.type_specific_key.options
    # So, we might have `select: {'options': [...]}` or `status: {'options': [...]}`.
    # This model represents the value part of the `properties` dictionary in a Notion Database object.

    # Capturing type-specific details like options for select/multi_select/status
    select: NotionPropertySchemaTypeDetails | None = Field(default=None)
    multi_select: NotionPropertySchemaTypeDetails | None = Field(default=None)
    status: NotionPropertySchemaTypeDetails | None = Field(default=None)
    formula: dict[str, Any] | None = Field(default=None)
    relation: dict[str, Any] | None = Field(default=None)
    rollup: dict[str, Any] | None = Field(default=None)
    # ... other property types like 'rich_text', 'title', 'number', 'date', etc., have their own specific structures
    # which are often just an empty object `{}` if no further config is needed for that type.

    class Config:
        extra = "allow"  # Allow fields like 'rich_text', 'title', etc., which are often empty dicts.


class OpenAISchemaProperty(BaseModel):
    """Represents a property in an OpenAI function calling schema."""

    type: str = Field(description="Data type of the property (e.g., 'string', 'number', 'array', 'object').")
    description: str | None = Field(default=None, description="Description of the property.")
    enum: list[str] | None = Field(default=None, description="For 'string' type, a list of possible values.")
    # For 'array' type, an 'items' field would describe the element type.
    # For 'object' type, a 'properties' field would describe sub-properties.
    items: OpenAISchemaProperty | None = Field(default=None, description="Schema for items if type is 'array'.")
    # properties: dict[str, 'OpenAISchemaProperty'] | None = Field(default=None, description="Schema for sub-properties if type is 'object'.") # Forward ref

    class Config:
        extra = "allow"


# Update for forward reference if needed for nested object properties
# OpenAISchemaProperty.update_forward_refs()


class OpenAIFunctionSchema(BaseModel):
    """Represents the overall schema for an OpenAI function call."""

    name: str = Field(description="Name of the function.")
    description: str | None = Field(default=None, description="Description of what the function does.")
    parameters: OpenAISchemaProperty = Field(
        description="Parameters the function accepts, as a JSON schema object of type 'object'."
    )


class OpenAISchemaForTools(BaseModel):
    """Corresponds to the 'parameters' part of an OpenAI tool definition (JSON schema)."""

    type: Literal["object"] = Field(default="object", description="Schema type, must be 'object'.")
    properties: dict[str, OpenAISchemaProperty] = Field(description="Dictionary of parameter names to their schemas.")
    required: list[str] | None = Field(default=None, description="List of required parameter names.")
    additionalProperties: bool = Field(default=False, description="Whether additional properties are allowed.")
