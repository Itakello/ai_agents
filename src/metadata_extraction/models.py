"""Schema and data conversion utilities for OpenAI and Notion integration.

This module provides functions to convert between Notion property schemas and OpenAI JSON schemas,
as well as converting data between the two formats.
"""

from typing import Any


def notion_property_to_openai_schema(notion_property: dict[str, Any], add_options: bool) -> dict[str, Any]:
    """Convert a Notion property definition to OpenAI JSON Schema format.

    Args:
        notion_property: Notion property definition with 'type' and other config

    Returns:
        OpenAI-compatible JSON Schema definition
    """
    property_type = notion_property.get("type")
    description = notion_property.get("description", "")
    property: dict[str, Any] = {}

    match property_type:
        case "rich_text" | "title":
            property = {"type": "string"}
        case "number":
            property = {"type": "number"}
        case "checkbox":
            property = {"type": "boolean"}
        case "select":
            options = notion_property.get("select", {}).get("options", [])
            if options and add_options:
                property = {"type": "string", "enum": [option["name"] for option in options]}
            else:
                property = {"type": "string"}
        case "status":
            options = notion_property.get("status", {}).get("options", [])
            if options and add_options:
                property = {"type": "string", "enum": [option["name"] for option in options]}
            else:
                property = {"type": "string"}
        case "multi_select":
            options = notion_property.get("multi_select", {}).get("options", [])
            if options and add_options:
                property = {
                    "type": "array",
                    "items": {"type": "string", "enum": [option["name"] for option in options]},
                }
            else:
                property = {"type": "array", "items": {"type": "string"}}
        case "date":
            property = {"type": "string", "format": "date"}
        case "email":
            property = {"type": "string", "format": "email"}
        case "phone_number":
            property = {"type": "string"}
        case "url":
            property = {"type": "string", "pattern": r"^(https?)://[^\s/$.?#].[^\s]*$"}
        case "people":
            property = {"type": "array", "items": {"type": "string"}}
        case "files":
            property = {"type": "array", "items": {"type": "string", "format": "uri"}}
        case _:
            # Default to string for unsupported types
            property = {"type": "string"}
    if description:
        property["description"] = description
    return property


def openai_data_to_notion_property(value: Any, property_type: str) -> dict[str, Any]:
    """Convert OpenAI response data to Notion property value format.

    Args:
        value: Value from OpenAI response
        property_type: Notion property type (rich_text, number, etc.)

    Returns:
        Notion-formatted property value
    """
    if value is None:
        return {}

    match property_type:
        case "rich_text" | "title":
            return {"rich_text": [{"text": {"content": str(value)}}]}
        case "number":
            return {"number": float(value) if value is not None else None}
        case "checkbox":
            return {"checkbox": bool(value)}
        case "select":
            return {"select": {"name": str(value)}} if value else {}
        case "status":
            return {"status": {"name": str(value)}} if value else {}
        case "multi_select":
            if isinstance(value, list):
                return {"multi_select": [{"name": str(item)} for item in value if item]}
            return {}
        case "date":
            return {"date": {"start": str(value)}} if value else {}
        case "email":
            return {"email": str(value)} if value else {}
        case "phone_number":
            return {"phone_number": str(value)} if value else {}
        case "url":
            return {"url": str(value)} if value else {}
        case "people":
            # For people, we need user objects, but for simplicity return empty
            # In practice, you'd need to resolve names to Notion user IDs
            return {}
        case "files":
            if isinstance(value, list) and value:
                return {
                    "files": [
                        {"type": "external", "name": str(url).split("/")[-1], "external": {"url": str(url)}}
                        for url in value
                        if url
                    ]
                }
            return {}
        case _:
            # Default to rich_text for unknown types
            return {"rich_text": [{"text": {"content": str(value)}}]}


def create_openai_schema_from_notion_database(
    notion_properties: dict[str, Any], add_options: bool = True
) -> dict[str, Any]:
    """Create a complete OpenAI JSON Schema from Notion database properties.

    Args:
        notion_properties: Dictionary of Notion property definitions

    Returns:
        Complete OpenAI JSON Schema for structured output
    """
    schema: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

    for prop_name, prop_config in notion_properties.items():
        # Skip read-only properties
        prop_type = prop_config.get("type")
        prop_desc = prop_config.get("description", "").strip().lower()
        if prop_type in ["created_time", "created_by", "last_edited_time", "last_edited_by", "formula", "rollup"]:
            continue
        if "#exclude" in prop_desc:
            continue

        schema["properties"][prop_name] = notion_property_to_openai_schema(prop_config, add_options=add_options)
        schema["required"].append(prop_name)

    return schema


def convert_openai_response_to_notion_update(
    openai_response: dict[str, Any], notion_properties: dict[str, Any]
) -> dict[str, Any]:
    """Convert OpenAI response to Notion page update format.

    Args:
        openai_response: Data returned from OpenAI structured output
        notion_properties: Notion database property definitions

    Returns:
        Dictionary ready for Notion page update API call
    """
    notion_update: dict[str, Any] = {"properties": {}}

    for prop_name, value in openai_response.items():
        if prop_name in notion_properties and value is not None:
            prop_type = notion_properties[prop_name].get("type")
            notion_update["properties"][prop_name] = openai_data_to_notion_property(value, prop_type)

    return notion_update
