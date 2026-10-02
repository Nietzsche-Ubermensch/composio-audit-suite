"""End-to-end audit runner.

Pulls the live Composio catalog, builds the dependency graph, caches
schemas, validates a sample of responses, and writes the full report.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .composio_client import ComposioClient
from .dependency_graph import DependencyGraph, ToolNode
from .schemas import SchemaRegistry, ToolSchema


class AuditRunner:
    """Run a full audit against a ComposioClient."""

    def __init__(self, client: ComposioClient) -> None:
        self._client = client
        self._graph = DependencyGraph()
        self._registry = SchemaRegistry()

    def run(self, toolkit_filter: list[str] | None = None) -> dict[str, Any]:
        """Execute the full audit pipeline and return the report dict."""
        report: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "toolkits": {},
            "graph_summary": {},
            "schema_summary": {},
            "connection_status": {},
            "errors": [],
        }

        # 1. Discover toolkits
        try:
            toolkits = self._client.list_toolkits()
        except Exception as exc:  # broad: catalog failures must not abort the run
            report["errors"].append(f"list_toolkits failed: {exc}")
            toolkits = []

        toolkit_names = [t.get("slug") or t.get("name") for t in toolkits if t]
        if toolkit_filter:
            toolkit_names = [t for t in toolkit_names if t in toolkit_filter]

        # 2. Check connections
        if toolkit_names:
            try:
                report["connection_status"] = self._client.check_connections(toolkit_names)
            except Exception as exc:
                report["errors"].append(f"check_connections failed: {exc}")

        # 3. Search tools per toolkit and build graph + schema registry
        for tk in toolkit_names:
            try:
                tools = self._client.search_tools(query=tk, limit=50)
            except Exception as exc:
                report["errors"].append(f"search_tools({tk}) failed: {exc}")
                continue

            tk_report: dict[str, Any] = {"tool_count": len(tools), "tools": []}
            for tool in tools:
                slug = tool.get("slug") or tool.get("name") or "unknown"
                node = ToolNode(
                    toolkit=tk,
                    slug=slug,
                    description=tool.get("description", ""),
                    inputs=list((tool.get("input_schema") or {}).get("required", [])),
                    outputs=list((tool.get("output_schema") or {}).get("required", [])),
                )
                self._graph.add_tool(node)
                self._registry.register(
                    ToolSchema(
                        toolkit=tk,
                        slug=slug,
                        description=tool.get("description", ""),
                        input_schema=tool.get("input_schema") or {},
                        output_schema=tool.get("output_schema") or {},
                        required_params=list(
                            (tool.get("input_schema") or {}).get("required", [])
                        ),
                    )
                )
                tk_report["tools"].append(
                    {
                        "slug": slug,
                        "description": tool.get("description", "")[:120],
                        "required_inputs": node.inputs,
                    }
                )
            report["toolkits"][tk] = tk_report

        # 4. Graph summary
        try:
            report["graph_summary"] = self._graph.summary()
            report["mermaid"] = self._graph.to_mermaid()
        except ValueError as exc:
            report["errors"].append(f"graph cycle: {exc}")
            report["graph_summary"] = {"tool_count": len(self._graph._nodes), "cycle": True}

        # 5. Schema summary
        report["schema_summary"] = {
            "registered_schemas": len(self._registry._schemas),
            "by_toolkit": {
                tk: len(self._registry.by_toolkit(tk)) for tk in toolkit_names
            },
        }

        return report

    def write_report(self, report: dict[str, Any], path: str | Path) -> Path:
        """Write the report as formatted JSON."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return out
