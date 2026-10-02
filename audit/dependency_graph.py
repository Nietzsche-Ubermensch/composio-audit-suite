"""Build dependency graphs across Composio toolkits.

Maps which tools depend on outputs of other tools (e.g., a file SHA
produced by one tool consumed by another) so callers can sequence
multi-step operations safely.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolNode:
    """A single tool in the dependency graph."""

    toolkit: str
    slug: str
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


class DependencyGraph:
    """Directed graph of tool dependencies.

    An edge A -> B means B consumes an output that A produces.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, ToolNode] = {}  # key: "toolkit.slug"
        self._edges: dict[str, set[str]] = defaultdict(set)

    def add_tool(self, node: ToolNode) -> None:
        key = f"{node.toolkit}.{node.slug}"
        self._nodes[key] = node

    def add_dependency(self, producer: str, consumer: str) -> None:
        """Record that `consumer` depends on `producer` (both 'toolkit.slug')."""
        if producer not in self._nodes or consumer not in self._nodes:
            raise KeyError(f"Unknown tool: {producer!r} or {consumer!r}")
        self._edges[producer].add(consumer)

    def topological_order(self) -> list[str]:
        """Return tools in an order where every dependency runs first.

        Raises ValueError on cycles.
        """
        indegree = {k: 0 for k in self._nodes}
        for src, dsts in self._edges.items():
            for dst in dsts:
                indegree[dst] += 1

        queue: deque[str] = deque(k for k, d in indegree.items() if d == 0)
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in self._edges[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if len(order) != len(self._nodes):
            raise ValueError("Dependency cycle detected in tool graph")
        return order

    def to_mermaid(self) -> str:
        """Render the graph as a Mermaid flowchart."""
        lines = ["flowchart TD"]
        for key, node in self._nodes.items():
            label = f"{node.toolkit}<br/>{node.slug}"
            lines.append(f'    {key.replace(".", "_")}["{label}"]')
        for src, dsts in self._edges.items():
            for dst in dsts:
                lines.append(f"    {src.replace('.', '_') } --> {dst.replace('.', '_')}")
        return "\n".join(lines)

    def summary(self) -> dict[str, Any]:
        return {
            "tool_count": len(self._nodes),
            "edge_count": sum(len(v) for v in self._edges.values()),
            "order": self.topological_order(),
        }
