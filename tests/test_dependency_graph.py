"""Tests for the dependency graph module."""

import pytest

from audit.dependency_graph import DependencyGraph, ToolNode


def test_topological_order_respects_edges():
    g = DependencyGraph()
    g.add_tool(ToolNode("a", "one", outputs=["x"]))
    g.add_tool(ToolNode("a", "two", inputs=["x"]))
    g.add_dependency("a.one", "a.two")
    assert g.topological_order() == ["a.one", "a.two"]


def test_cycle_detected():
    g = DependencyGraph()
    g.add_tool(ToolNode("a", "one"))
    g.add_tool(ToolNode("a", "two"))
    g.add_dependency("a.one", "a.two")
    g.add_dependency("a.two", "a.one")
    with pytest.raises(ValueError, match="cycle"):
        g.topological_order()


def test_mermaid_contains_nodes():
    g = DependencyGraph()
    g.add_tool(ToolNode("gh", "get_file"))
    mermaid = g.to_mermaid()
    assert "gh_get_file" in mermaid
    assert "flowchart TD" in mermaid
