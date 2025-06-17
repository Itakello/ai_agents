"""Database schema verification and fixing functionality for Notion."""

from typing import Any

from loguru import logger

from src.common.models import NotionDatabaseSchemaProperty


class DatabaseVerifier:
    """Verifies and fixes Notion database schema."""

    REQUIRED_PROPERTIES = {
        "Title": "title",
        "Company": "rich_text",
        "Job URL": "url",
        "Resume": "files",
    }

    def check_schema(self, schema: dict[str, Any]) -> tuple[set[str], dict[str, str]]:
        """Check if the database schema has all required properties with correct types.

        Args:
            schema: The database schema from Notion API.

        Returns:
            Tuple containing:
            - Set of missing property names
            - Dict mapping property names to their incorrect types
        """
        properties = schema.get("properties", {})
        missing_props = set(self.REQUIRED_PROPERTIES.keys()) - set(properties.keys())
        type_mismatches = {}

        for prop_name, expected_type in self.REQUIRED_PROPERTIES.items():
            if prop_name in properties:
                actual_type = properties[prop_name].get("type")
                if actual_type != expected_type:
                    type_mismatches[prop_name] = actual_type

        return missing_props, type_mismatches

    def fix_schema(
        self, schema: dict[str, Any], missing_props: set[str], type_mismatches: dict[str, str]
    ) -> dict[str, Any]:
        """Fix the database schema by adding missing properties and correcting type mismatches.

        Args:
            schema: The current database schema.
            missing_props: Set of missing property names.
            type_mismatches: Dict mapping property names to their incorrect types.

        Returns:
            Updated schema with fixes applied.
        """
        properties = schema.get("properties", {})

        # Add missing properties
        for prop_name in missing_props:
            expected_type = self.REQUIRED_PROPERTIES[prop_name]
            properties[prop_name] = {
                "type": expected_type,
                "name": prop_name,
            }
            logger.info(f"Adding missing property: {prop_name} ({expected_type})")

        # Fix type mismatches
        for prop_name, current_type in type_mismatches.items():
            expected_type = self.REQUIRED_PROPERTIES[prop_name]
            properties[prop_name]["type"] = expected_type
            logger.info(f"Fixing property type: {prop_name} ({current_type} -> {expected_type})")

        schema["properties"] = properties
        return schema

    def validate_property(self, property_data: dict[str, Any]) -> NotionDatabaseSchemaProperty:
        """Validate a single property against the NotionDatabaseSchemaProperty model.

        Args:
            property_data: The property data from Notion API.

        Returns:
            Validated NotionDatabaseSchemaProperty instance.

        Raises:
            ValueError: If the property data is invalid.
        """
        try:
            return NotionDatabaseSchemaProperty(**property_data)
        except Exception as e:
            raise ValueError(f"Invalid property data: {e}") from e
