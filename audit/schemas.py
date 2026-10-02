"""Tool and response schema handling for Composio toolkits.

Pulls input/output schemas from the Composio tool catalog and
normalizes them into a consistent internal format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSchema:
    """Normalized schema for one Composio tool."""

    toolkit: str
    slug: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    required_params: list[str] = field(default_factory=list)


class SchemaRegistry:
    """In-memory registry of tool schemas, keyed by 'toolkit.slug'."""

    def __init__(self) -> None:
        self._schemas: dict[str, ToolSchema] = {}

    def register(self, schema: ToolSchema) -> None:
        self._schemas[f"{schema.toolkit}.{schema.slug}"] = schema

    def get(self, toolkit: str, slug: str) -> ToolSchema | None:
        return self._schemas.get(f"{toolkit}.{slug}")

    def by_toolkit(self, toolkit: str) -> list[ToolSchema]:
        return [s for s in self._schemas.values() if s.toolkit == toolkit]

    def validate_response(self, toolkit: str, slug: str, response: Any) -> list[str]:
        """Return a list of validation errors for `response` against the tool's output schema.

        Currently checks required top-level keys. Extend with type checks as needed.
        """
        schema = self.get(toolkit, slug)
        if schema is None:
            return [f"No schema registered for {toolkit}.{slug}"]
        errors: list[str] = []
        required = schema.output_schema.get("required", [])
        if isinstance(response, dict):
            for key in required:
                if key not in response:
                    errors.append(f"Missing required output key: {key}")
        elif required:
            errors.append("Response is not an object but output schema requires keys")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            f"{s.toolkit}.{s.slug}": {
                "description": s.description,
                "required_params": s.required_params,
                "input_schema": s.input_schema,
                "output_schema": s.output_schema,
            }
            for s in self._schemas.values()
        }
