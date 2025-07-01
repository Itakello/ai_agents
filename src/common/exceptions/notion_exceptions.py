"""Notion API exceptions."""


class NotionAPIError(Exception):
    """Base exception for Notion API errors."""

    pass


class NotionFileError(Exception):
    """Exception for Notion file operations."""

    pass


class NotionSchemaError(Exception):
    """Exception for Notion schema operations."""

    pass
