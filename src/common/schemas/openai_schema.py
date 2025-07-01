from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OpenAISchema(BaseModel):
    """Pydantic representation of an OpenAI JSON Schema.

    This mirrors the JSON schema that is sent to the OpenAI *Responses* API for
    structured output.  Encapsulating it in a model allows us to:

    • Keep strong typing throughout the codebase (no loose ``dict`` objects).
    • Perform validation / manipulation via Pydantic helpers.
    • Easily convert back to the raw ``dict`` with ``.model_dump()`` when
      making the API call.
    """

    type: str = Field(default="object", description="The schema root type (always 'object').")
    properties: dict[str, Any] = Field(default_factory=dict, description="Mapping of field names → schema.")
    required: list[str] = Field(default_factory=list, description="Required property names.")
    additionalProperties: bool = Field(default=False, description="Whether additional props are allowed.")


# ---------------------------------------------------------------------------
# Post-class definition: attach an alias so callers can use ``schema.dict()``
# without shadowing the builtin ``dict`` during class creation (which breaks
# Pydantic's type-hint evaluation).
# ---------------------------------------------------------------------------


def _openai_schema_dict(self: OpenAISchema, *args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: D401
    """Return the raw schema as a dictionary – thin alias around ``model_dump``."""

    return self.model_dump(*args, **kwargs)


# Attach the alias **after** the class body so that the name ``dict`` is *not*
# present in the class namespace during the metaclass' field-collection phase
# (avoiding the 'function object is not subscriptable' error).
setattr(OpenAISchema, "dict", _openai_schema_dict)
