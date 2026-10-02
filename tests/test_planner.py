"""Tests for the planner module."""

import pytest

from audit.planner import Planner
from audit.dependency_graph import DependencyGraph, ToolNode
from audit.schemas import SchemaRegistry, ToolSchema


def _setup():
    g = DependencyGraph()
    g.add_tool(ToolNode("t", "a", outputs=["x"]))
    g.add_tool(ToolNode("t", "b", inputs=["x"]))
    g.add_dependency("t.a", "t.b")
    reg = SchemaRegistry()
    reg.register(ToolSchema(toolkit="t", slug="b", description="", output_schema={"required": ["ok"]}))
    return Planner(g, reg)


def test_plan_builds_and_serializes():
    planner = _setup()
    plan = planner.plan(
        goal="demo",
        steps=[
            {"order": 1, "toolkit": "t", "slug": "a", "purpose": "first"},
            {"order": 2, "toolkit": "t", "slug": "b", "purpose": "second", "depends_on": [1]},
        ],
    )
    d = plan.to_dict()
    assert d["goal"] == "demo"
    assert len(d["steps"]) == 2
    assert d["steps"][1]["depends_on"] == [1]


def test_plan_rejects_forward_dependency():
    planner = _setup()
    with pytest.raises(ValueError, match="runs later"):
        planner.plan(
            goal="bad",
            steps=[
                {"order": 1, "toolkit": "t", "slug": "b", "purpose": "x", "depends_on": [2]},
                {"order": 2, "toolkit": "t", "slug": "a", "purpose": "y"},
            ],
        )
