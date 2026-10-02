"""Command-line entry point for the audit suite."""

from __future__ import annotations

import argparse
import json
import sys

from .dependency_graph import DependencyGraph, ToolNode
from .schemas import SchemaRegistry, ToolSchema
from .planner import Planner


def _demo() -> None:
    """Run a small end-to-end demo with synthetic data."""
    graph = DependencyGraph()
    graph.add_tool(ToolNode("github", "get_file_contents", outputs=["sha"]))
    graph.add_tool(ToolNode("github", "create_or_update_file", inputs=["sha"]))
    graph.add_dependency("github.get_file_contents", "github.create_or_update_file")

    registry = SchemaRegistry()
    registry.register(
        ToolSchema(
            toolkit="github",
            slug="create_or_update_file",
            description="Create or update a file in a repo",
            input_schema={"required": ["owner", "repo", "path", "content", "message", "branch"]},
            output_schema={"required": ["commit", "content"]},
            required_params=["owner", "repo", "path", "content", "message", "branch"],
        )
    )

    print(json.dumps(graph.summary(), indent=2))
    print(graph.to_mermaid())

    planner = Planner(graph, registry)
    plan = planner.plan(
        goal="Update README.md in a repo",
        steps=[
            {"order": 1, "toolkit": "github", "slug": "get_file_contents", "purpose": "Fetch current file SHA"},
            {"order": 2, "toolkit": "github", "slug": "create_or_update_file", "purpose": "Write new content", "depends_on": [1]},
        ],
    )
    print(json.dumps(plan.to_dict(), indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Composio audit suite")
    parser.add_argument("--demo", action="store_true", help="Run synthetic demo")
    args = parser.parse_args(argv)
    if args.demo:
        _demo()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
