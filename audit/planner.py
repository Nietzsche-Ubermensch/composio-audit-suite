"""Execution plan generator across Composio toolkits.

Turns a high-level goal into an ordered sequence of tool calls,
respecting the dependency graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .dependency_graph import DependencyGraph
from .schemas import SchemaRegistry


@dataclass
class PlanStep:
    """One step in an execution plan."""

    order: int
    toolkit: str
    slug: str
    purpose: str
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)


@dataclass
class Plan:
    """A complete execution plan."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [
                {
                    "order": s.order,
                    "toolkit": s.toolkit,
                    "slug": s.slug,
                    "purpose": s.purpose,
                    "params": s.params,
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
        }


class Planner:
    """Generate and validate execution plans."""

    def __init__(self, graph: DependencyGraph, registry: SchemaRegistry) -> None:
        self._graph = graph
        self._registry = registry

    def plan(self, goal: str, steps: list[dict[str, Any]]) -> Plan:
        """Build a Plan from a list of step dicts.

        Each step dict: toolkit, slug, purpose, params (optional), depends_on (optional, list of step orders).
        """
        plan = Plan(goal=goal)
        for raw in steps:
            plan.steps.append(
                PlanStep(
                    order=raw["order"],
                    toolkit=raw["toolkit"],
                    slug=raw["slug"],
                    purpose=raw["purpose"],
                    params=raw.get("params", {}),
                    depends_on=raw.get("depends_on", []),
                )
            )
        self._validate(plan)
        return plan

    def _validate(self, plan: Plan) -> None:
        orders = {s.order for s in plan.steps}
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in orders:
                    raise ValueError(f"Step {step.order} depends on unknown step {dep}")
                if dep >= step.order:
                    raise ValueError(f"Step {step.order} depends on step {dep} which runs later or at the same time")
