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
import re
from pathlib import Path
from typing import Any

REQUIRED_AUTOMATION_KEYS = ("taskId", "name", "isActive", "trigger", "prompt_summary")
REQUIRED_TRIGGER_KEYS = ("provider", "trigger_type", "dimensions")

# GitHub login: 1-39 alphanumeric/hyphen, cannot start or end with a hyphen.
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
# GitHub repo name: 1-100 of alphanumeric, dot, underscore, hyphen; not . or ..
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _count(value: Any) -> bool:
    """True for real ints. bool is an int subclass and is not a count."""
    return isinstance(value, int) and not isinstance(value, bool)


def _repo_token(repo: str) -> str | None:
    """Accept a GitHub numeric repo id or an owner/name slug. Reject blanks.

    Numeric ids must be ASCII digits. str.isdigit() is true for superscript
    and other non-decimal digits that int() rejects, which would crash the
    validator instead of returning an error.
    """
    token = repo.strip()
    if not token or any(char.isspace() for char in token):
        return None
    if token.isascii() and token.isdigit():
        return token if int(token) > 0 else None
    if token.count("/") != 1:
        return None
    owner, name = token.split("/")
    if owner in {".", ".."} or name in {".", ".."} or name.startswith("."):
        return None
    if not _OWNER_RE.fullmatch(owner) or not _NAME_RE.fullmatch(name):
        return None
    return token


def _repo_names(dimensions: Any) -> list[str] | None:
    """Return usable repo tokens, or None if dimensions.repo is unusable."""
    if not isinstance(dimensions, dict):
        return None
    repos = dimensions.get("repo")
    if not isinstance(repos, list) or not repos:
        return None
    names: list[str] = []
    seen: set[str] = set()
    for repo in repos:
        if not isinstance(repo, str):
            return None
        token = _repo_token(repo)
        if token is None or token in seen:
            return None
        seen.add(token)
        names.append(token)
    return names


def inventory_errors(payload: dict[str, Any]) -> list[str]:
    """Return consistency errors for a meta-tool inventory document."""
    errors: list[str] = []
    tools = payload.get("tools")
    if not isinstance(tools, dict) or not tools:
        return ["tools must be a non-empty object keyed by slug"]

    slugs = list(tools)
    if len(slugs) != len(set(slugs)):
        errors.append("tools contains duplicate slugs")

    if "unique_slugs" not in payload:
        errors.append("unique_slugs is required")
        unique = None
    else:
        unique = payload.get("unique_slugs")
        if not _count(unique):
            errors.append("unique_slugs must be an int")
        elif unique != len(slugs):
            errors.append(f"unique_slugs {unique} != tools object size {len(slugs)}")
    retrieved = payload.get("schemas_retrieved")
    total = payload.get("meta_tools_total")
    if not _count(retrieved) or retrieved != len(slugs):
        errors.append(
            f"schemas_retrieved {retrieved} != unique tools stored {len(slugs)}"
        )
    if not _count(total) or total != len(slugs):
        errors.append(f"meta_tools_total {total} != unique tools stored {len(slugs)}")

    screen_rows = payload.get("screen_rows")
    duplicate = payload.get("duplicate_screen_entry")
    has_rows = screen_rows is not None
    has_duplicate = duplicate is not None
    if has_rows and has_duplicate:
        if not _count(screen_rows) or screen_rows <= len(slugs):
            errors.append(
                "screen_rows must be an int greater than the unique slug count "
                "when duplicate_screen_entry is set"
            )
        if not isinstance(duplicate, str) or not duplicate.strip():
            errors.append("duplicate_screen_entry must be a non-empty slug")
        elif duplicate not in tools:
            errors.append(f"duplicate_screen_entry {duplicate} is not in tools")
    elif has_rows or has_duplicate:
        errors.append("screen_rows and duplicate_screen_entry must be set together")

    for slug, entry in tools.items():
        if not isinstance(slug, str) or not slug.strip():
            errors.append("tools keys must be non-empty slug strings")
            continue
        if not isinstance(entry, dict):
            errors.append(f"{slug} entry must be an object")
            continue
        if not any(key in entry for key in ("status", "equivalent", "replaced_by")):
            errors.append(f"{slug} needs status, equivalent, or replaced_by")
    return errors


def automation_errors(payload: dict[str, Any]) -> list[str]:
    """Return consistency errors for an automations snapshot."""
    errors: list[str] = []
    automations = payload.get("automations")
    if not isinstance(automations, list):
        return ["automations must be a list"]
    count = payload.get("count")
    if not _count(count) or count != len(automations):
        errors.append(
            f"count {count} != automations length {len(automations)}"
        )
    providers = payload.get("catalog_providers_available")
    if not isinstance(providers, list) or "github" not in providers:
        errors.append("catalog_providers_available must include github")
    trigger_types = payload.get("github_trigger_types")
    if not isinstance(trigger_types, list) or "push_to_branch" not in trigger_types:
        errors.append("github_trigger_types must include push_to_branch")

    seen: set[str] = set()
    for index, item in enumerate(automations):
        if not isinstance(item, dict):
            errors.append(f"automations[{index}] must be an object")
            continue
        missing = [key for key in REQUIRED_AUTOMATION_KEYS if key not in item]
        if missing:
            errors.append(f"automations[{index}] missing {missing}")
            continue
        task_id = item["taskId"]
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"automations[{index}].taskId must be a non-empty string")
        else:
            normalized = task_id.strip()
            if task_id != normalized:
                errors.append(
                    f"automations[{index}].taskId must not have surrounding whitespace"
                )
            if normalized in seen:
                errors.append(f"duplicate taskId {normalized}")
            else:
                seen.add(normalized)
        trigger = item["trigger"]
        if not isinstance(trigger, dict):
            errors.append(f"automations[{index}].trigger must be an object")
            continue
        missing_trigger = [key for key in REQUIRED_TRIGGER_KEYS if key not in trigger]
        if missing_trigger:
            errors.append(f"automations[{index}].trigger missing {missing_trigger}")
            continue
        if _repo_names(trigger.get("dimensions")) is None:
            errors.append(f"automations[{index}] trigger has no dimensions.repo")
    return errors
