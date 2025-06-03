import random
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
                filtered = [v for v in value if v not in (None, "")]
                if not filtered:
                    return {}
                return {"multi_select": [{"name": str(v)} for v in filtered]}
            else:
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
            # Always return empty dict for people (complex type, not handled)
            return {}
        case "files":
            if isinstance(value, list) and value:
                return {
                    "files": [
                        {
                            "type": "external",
                            "name": str(url).split("/")[-1],
                            "external": {"url": str(url)},
                        }
                        for url in value
                        if url
                    ]
                }
            else:
                return {}
        case _:
            # Default to rich_text for unknown types
            return {"rich_text": [{"text": {"content": str(value)}}]}


def _should_exclude_property(prop_type: str, prop_desc: str) -> bool:
    """Check if a property should be excluded from schema generation.

    Args:
        prop_type: The Notion property type
        prop_desc: The property description (case-insensitive)

    Returns:
        True if the property should be excluded
    """
    readonly_types = {"created_time", "created_by", "last_edited_time", "last_edited_by", "formula", "rollup"}
    return prop_type in readonly_types or "#exclude" in prop_desc


def _should_keep_options(prop_desc: str) -> bool:
    """Check if a property should keep its enum options.

    Args:
        prop_desc: The property description (case-insensitive)

    Returns:
        True if options should be preserved
    """
    return "#keep-options" in prop_desc


def _generate_example_description(prop_config: dict[str, Any], prop_type: str) -> str:
    """Generate example description for select/multi_select/status properties.

    Args:
        prop_config: The property configuration
        prop_type: The property type

    Returns:
        Example description string
    """
    options = prop_config.get(prop_type, {}).get("options", [])
    if not options:
        return ""

    # Sample up to 3 random options for examples
    sample_size = min(3, len(options))
    sampled_examples = random.sample(options, sample_size)
    example_names = [option["name"] for option in sampled_examples]

    return "e.g. " + ", ".join(example_names) + ", ..."


def create_openai_schema_from_notion_database(notion_properties: dict[str, Any], add_options: bool) -> dict[str, Any]:
    """Create a complete OpenAI JSON Schema from Notion database properties.

    This function converts Notion database properties into an OpenAI-compatible JSON schema
    for structured output. It handles special description directives and option sampling.

    Args:
        notion_properties: Dictionary of Notion property definitions
        add_options: Whether to include enum options for select properties

    Returns:
        Complete OpenAI JSON Schema for structured output

    Special description directives:
        - #exclude: Property will be skipped entirely
        - #keep-options: Property options will always be included as enums (overrides add_options=False)

    Example:
        >>> properties = {
        ...     "status": {
        ...         "type": "select",
        ...         "description": "Task status #keep-options",
        ...         "select": {"options": [{"name": "Todo"}, {"name": "Done"}]}
        ...     }
        ... }
        >>> schema = create_openai_schema_from_notion_database(properties, add_options=False)
        >>> schema["properties"]["status"]["enum"]
        ["Todo", "Done"]
    """
    schema: dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

    for prop_name, prop_config in notion_properties.items():
        prop_type = prop_config.get("type")
        prop_desc = prop_config.get("description", "").strip().lower()

        # Skip excluded properties
        if _should_exclude_property(prop_type, prop_desc):
            continue

        # Determine if we should add options for this specific property
        force_keep_options = _should_keep_options(prop_desc)
        include_options = add_options or force_keep_options

        # Generate example descriptions for select-type properties when not including options
        if not include_options and prop_type in ["select", "multi_select", "status"] and not force_keep_options:
            example_desc = _generate_example_description(prop_config, prop_type)
            if example_desc:
                # Preserve original description if it exists
                original_desc = prop_config.get("description", "").strip()
                if original_desc and not original_desc.lower().startswith("#"):
                    prop_config["description"] = f"{original_desc} | {example_desc}"
                else:
                    prop_config["description"] = example_desc

        # Convert to OpenAI schema
        schema["properties"][prop_name] = notion_property_to_openai_schema(prop_config, add_options=include_options)
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
