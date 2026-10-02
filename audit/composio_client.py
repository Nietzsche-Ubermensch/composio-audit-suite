"""Live integration with the Composio tool catalog.

Wraps the Composio MCP meta-tools available in this environment:
SEARCH_TOOLS, GET_TOOL_SCHEMAS, LIST_TOOLKITS, MANAGE_CONNECTIONS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass
class ComposioClient:
    """Thin adapter over the Composio MCP tool surface.

    `executor` is a callable(tool_name, arguments) -> result dict.
    In production this is the connected Composio MCP layer; in tests it
    can be a stub returning canned catalog data.
    """

    executor: ToolExecutor
    _cache: dict[str, Any] = field(default_factory=dict, repr=False)

    def search_tools(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search the Composio tool catalog."""
        key = f"search:{query}:{limit}"
        if key not in self._cache:
            result = self.executor(
                "composio___COMPOSIO_SEARCH_TOOLS",
                {"query": query, "limit": limit},
            )
            self._cache[key] = result
        return self._normalize_tool_list(self._cache[key])

    def get_tool_schemas(self, tool_names: list[str]) -> dict[str, Any]:
        """Fetch input/output schemas for specific tools."""
        key = "schemas:" + ",".join(sorted(tool_names))
        if key not in self._cache:
            result = self.executor(
                "composio___COMPOSIO_GET_TOOL_SCHEMAS",
                {"tool_names": tool_names},
            )
            self._cache[key] = result
        return self._normalize_schema_result(self._cache[key])

    def list_toolkits(self) -> list[dict[str, Any]]:
        """List all available Composio toolkits."""
        if "toolkits" not in self._cache:
            result = self.executor(
                "composio___COMPOSIO_LIST_TOOLKITS", {})
            self._cache["toolkits"] = result
        return self._normalize_toolkit_list(self._cache["toolkits"])

    def check_connections(self, toolkits: list[str]) -> dict[str, Any]:
        """Check which toolkits have active connections."""
        result = self.executor(
            "composio___COMPOSIO_CHECK_MULTIPLE_ACTIVE_CONNECTIONS",
            {"toolkits": toolkits},
        )
        return self._normalize_connection_result(result)

    # -- normalization helpers -------------------------------------------------

    @staticmethod
    def _normalize_tool_list(result: Any) -> list[dict[str, Any]]:
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for k in ("data", "tools", "results", "items"):
                if isinstance(result.get(k), list):
                    return result[k]
        return []

    @staticmethod
    def _normalize_schema_result(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            data = result.get("data", result)
            if isinstance(data, dict):
                return data
        return {"schemas": result} if result else {"schemas": {}}

    @staticmethod
    def _normalize_toolkit_list(result: Any) -> list[dict[str, Any]]:
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for k in ("data", "toolkits", "results", "items"):
                if isinstance(result.get(k), list):
                    return result[k]
        return []

    @staticmethod
    def _normalize_connection_result(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result.get("data", result)
        return {"connections": result} if result else {"connections": {}}


def from_json_file(path: str) -> ComposioClient:
    """Build a client backed by a static JSON catalog file (offline mode)."""
    with open(path, encoding="utf-8") as f:
        catalog = json.load(f)

    def executor(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name.endswith("SEARCH_TOOLS"):
            q = arguments.get("query", "").lower()
            tools = catalog.get("tools", [])
            hits = [t for t in tools if q in json.dumps(t).lower()]
            return {"data": hits[: arguments.get("limit", 20)]}
        if tool_name.endswith("GET_TOOL_SCHEMAS"):
            names = set(arguments.get("tool_names", []))
            schemas = {
                t["slug"]: t for t in catalog.get("tools", []) if t.get("slug") in names
            }
            return {"data": {"schemas": schemas}}
        if tool_name.endswith("LIST_TOOLKITS"):
            return {"data": catalog.get("toolkits", [])}
        if tool_name.endswith("CHECK_MULTIPLE_ACTIVE_CONNECTIONS"):
            wanted = set(arguments.get("toolkits", []))
            conns = catalog.get("connections", {})
            return {"data": {k: v for k, v in conns.items() if k in wanted}}
        return {"error": f"Unknown tool: {tool_name}"}

    return ComposioClient(executor=executor)
