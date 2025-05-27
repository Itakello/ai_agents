from typing import Any


class APIErrorCode:
    """Notion API error codes."""

    pass


class Client:
    """Notion API client."""

    def __init__(self, **kwargs: Any) -> None: ...
    def pages(self) -> "PagesEndpoint": ...
    def databases(self) -> "DatabasesEndpoint": ...
    def blocks(self) -> "BlocksEndpoint": ...

    # Add other endpoints as needed


class PagesEndpoint:
    def retrieve(self, page_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def update(self, page_id: str, **kwargs: Any) -> dict[str, Any]: ...

    # Add other page methods as needed


class DatabasesEndpoint:
    def query(self, database_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def retrieve(self, database_id: str, **kwargs: Any) -> dict[str, Any]: ...

    # Add other database methods as needed


class BlocksEndpoint:
    def retrieve(self, block_id: str, **kwargs: Any) -> dict[str, Any]: ...

    # Add other block methods as needed
