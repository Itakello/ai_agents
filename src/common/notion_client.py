from abc import abstractmethod
from typing import Any


class APIErrorCode:
    """Notion API error codes."""

    pass


class Client:
    """Notion API client."""

    def __init__(self, **kwargs: Any) -> None: ...
    @abstractmethod
    def pages(self) -> "PagesEndpoint": ...
    @abstractmethod
    def databases(self) -> "DatabasesEndpoint": ...
    @abstractmethod
    def blocks(self) -> "BlocksEndpoint": ...

    # Add other endpoints as needed


class PagesEndpoint:
    @abstractmethod
    def retrieve(self, page_id: str, **kwargs: Any) -> dict[str, Any]: ...

    @abstractmethod
    def update(self, page_id: str, **kwargs: Any) -> dict[str, Any]: ...

    # Add other page methods as needed


class DatabasesEndpoint:
    @abstractmethod
    def query(self, database_id: str, **kwargs: Any) -> dict[str, Any]: ...

    @abstractmethod
    def retrieve(self, database_id: str, **kwargs: Any) -> dict[str, Any]: ...

    # Add other database methods as needed


class BlocksEndpoint:
    @abstractmethod
    def retrieve(self, block_id: str, **kwargs: Any) -> dict[str, Any]: ...

    # Add other block methods as needed
