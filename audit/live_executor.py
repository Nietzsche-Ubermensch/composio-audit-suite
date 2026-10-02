"""Live Composio MCP executor.

Wraps the connected Composio MCP layer so the audit suite can run against
real toolkits instead of a static JSON catalog. The host environment
(Grok with Composio connected) supplies the actual tool-calling function;
this module just adapts it to the ComposioClient interface.
"""

from __future__ import annotations

from typing import Any, Callable


ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


def make_executor(call_tool: ToolExecutor) -> ToolExecutor:
    """Adapt a raw tool-caller into the ComposioClient executor signature.

    `call_tool` should be a function(tool_name: str, arguments: dict) -> dict
    that invokes the connected Composio MCP tool. This wrapper normalizes
    errors into the {"error": ...} shape the client expects.
    """

    def executor(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            result = call_tool(tool_name, arguments)
            if isinstance(result, dict) and result.get("error"):
                return result
            return result if isinstance(result, dict) else {"data": result}
        except Exception as exc:
            return {"error": f"{tool_name} failed: {exc}"}

    return executor
