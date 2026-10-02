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


def _catalog_names(value: Any) -> tuple[list[str], set[str]]:
    """Return catalog-entry errors and the tight names that can be matched.

    Padded or non-string entries used to be dropped, so membership disagreed
    with the raw list and a trigger could miss the catalog without a catalog error.
    """
    if not isinstance(value, list):
        return [], set()
    errors: list[str] = []
    names: set[str] = set()
    for item in value:
        if not _tight_string(item):
            errors.append("entries must be non-empty strings")
            continue
        names.add(item)
    return errors, names


def _repo_error(dimensions: Any) -> str | None:
    """Return an error when dimensions.repo is missing or not numeric ids.

    Automations resolves owner/name to a numeric repo id before create.
    A slug, a bare string, or a padded token is not a usable dimension.
    """
    if not isinstance(dimensions, dict) or "repo" not in dimensions:
        return "trigger has no dimensions.repo"
    repos = dimensions.get("repo")
    if not isinstance(repos, list):
        return "dimensions.repo must be a non-empty list"
    if not repos:
        return "trigger has no dimensions.repo"
    for repo in repos:
        if not _tight_string(repo):
            return "dimensions.repo entries must be non-empty strings"
        if not repo.isdigit():
            return "dimensions.repo entries must be numeric repo ids"
    return None


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
    provider_entry_errors, known_providers = _catalog_names(providers)
    if provider_entry_errors:
        errors.append("catalog_providers_available entries must be non-empty strings")
    if not isinstance(providers, list) or "github" not in known_providers:
        errors.append("catalog_providers_available must include github")
    trigger_types = payload.get("github_trigger_types")
    type_entry_errors, known_github_types = _catalog_names(trigger_types)
    if type_entry_errors:
        errors.append("github_trigger_types entries must be non-empty strings")
    if not isinstance(trigger_types, list) or "push_to_branch" not in known_github_types:
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
        if not _tight_string(task_id):
            errors.append(f"automations[{index}].taskId must be a non-empty string")
        elif task_id in seen:
            errors.append(f"duplicate taskId {task_id}")
        else:
            seen.add(task_id)
        name = item["name"]
        if not _tight_string(name):
            errors.append(f"automations[{index}].name must be a non-empty string")
        summary = item["prompt_summary"]
        if not _tight_string(summary):
            errors.append(
                f"automations[{index}].prompt_summary must be a non-empty string"
            )
        if not isinstance(item["isActive"], bool):
            errors.append(f"automations[{index}].isActive must be a bool")
        trigger = item["trigger"]
        if not isinstance(trigger, dict):
            errors.append(f"automations[{index}].trigger must be an object")
            continue
        missing_trigger = [key for key in REQUIRED_TRIGGER_KEYS if key not in trigger]
        if missing_trigger:
            errors.append(f"automations[{index}].trigger missing {missing_trigger}")
            continue
        provider = trigger.get("provider")
        if not _tight_string(provider) or provider not in known_providers:
            errors.append(
                f"automations[{index}].trigger.provider must be a catalog provider"
            )
        trigger_type = trigger.get("trigger_type")
        if not _tight_string(trigger_type):
            errors.append(
                f"automations[{index}].trigger.trigger_type must be a non-empty string"
            )
        elif provider == "github" and trigger_type not in known_github_types:
            errors.append(
                f"automations[{index}].trigger.trigger_type must be a github trigger type"
            )
        repo_error = _repo_error(trigger.get("dimensions"))
        if repo_error is not None:
            errors.append(f"automations[{index}] {repo_error}")
    return errors
