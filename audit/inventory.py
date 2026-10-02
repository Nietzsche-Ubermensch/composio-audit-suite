"""Loaders and consistency checks for persisted Composio inventory files.

The suite stores two offline snapshots under data/:

- composio-meta-inventory.json: unique meta-tool slugs and how each one is
  actually invoked (live connector vs equivalent Automations tool)
- automations.json: armed automations and the trigger catalog they came from

These checks catch the failure mode where a screen row count (a tool listed
twice on the toolkit page) is written as schemas_retrieved while the tools
object only contains unique slugs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_AUTOMATION_KEYS = ("taskId", "name", "isActive", "trigger", "prompt_summary")
REQUIRED_TRIGGER_KEYS = ("provider", "trigger_type", "dimensions")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _count(value: Any) -> bool:
    """True for real ints. bool is an int subclass and is not a count."""
    return isinstance(value, int) and not isinstance(value, bool)


def _tight_string(value: Any) -> bool:
    """Non-empty string with no leading or trailing whitespace."""
    return isinstance(value, str) and bool(value) and value == value.strip()



def _catalog_names(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if _tight_string(item)}


def _catalog_errors(value: Any, label: str, required: str) -> list[str]:
    """Require a list of tight unique names that includes required.

    Membership for trigger checks uses the tight set. A padded required token
    must not satisfy the include check, and padded siblings must not be
    silently dropped from an otherwise accepted catalog.
    """
    if not isinstance(value, list) or not value:
        return [f"{label} must include {required}"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not _tight_string(item):
            errors.append(f"{label}[{index}] must be a non-empty string")
            continue
        if item in seen:
            errors.append(f"{label} contains duplicate {item}")
        seen.add(item)
    if required not in seen:
        errors.append(f"{label} must include {required}")
    return errors


def _repo_error(dimensions: Any) -> str | None:
    """Return an error when dimensions.repo is missing or not usable names."""
    if not isinstance(dimensions, dict) or "repo" not in dimensions:
        return "trigger has no dimensions.repo"
    repos = dimensions.get("repo")
    if not isinstance(repos, list) or not repos:
        return "dimensions.repo must be a non-empty list"
    seen: set[str] = set()
    for repo in repos:
        if not _tight_string(repo):
            return "dimensions.repo entries must be non-empty strings"
        if repo in seen:
            return f"dimensions.repo contains duplicate {repo}"
        seen.add(repo)
    return None
