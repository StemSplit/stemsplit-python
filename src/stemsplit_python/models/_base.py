"""Shared pydantic configuration for every SDK model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class BaseSDKModel(BaseModel):
    """Frozen model with snake_case <-> camelCase aliasing.

    ``extra="allow"`` keeps the SDK forward-compatible: when the server adds
    a new field we surface it as a regular attribute on the model rather
    than crashing the user's code.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        populate_by_name=True,
        alias_generator=_to_camel,
        protected_namespaces=(),
    )


class ListPagination(BaseSDKModel):
    """Wire shape returned alongside list responses."""

    total: int
    limit: int
    offset: int
    has_more: bool


__all__ = ["BaseSDKModel", "ListPagination"]
