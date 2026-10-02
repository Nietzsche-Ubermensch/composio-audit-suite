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


def _string_list(value: Any) -> list[str] | None:
    """Return stripped non-empty strings, or None if any entry is unusable.

    Duplicates after stripping are rejected. Callers that need a distinct
    error should use _catalog_list_errors instead of treating None as missing.
    """
    if not isinstance(value, list) or not value:
        return None
    names: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        names.append(item.strip())
    if len(names) != len(set(names)):
        return None
    return names


def _catalog_list_errors(field: str, value: Any, required: str) -> tuple[list[str], list[str] | None]:
    """Validate a catalog list without collapsing every failure into 'missing'.

    Returns stripped names when every entry is a non-empty string, including
    when those names contain duplicates, so callers can still check membership.
    """
    if not isinstance(value, list) or not value:
        return [f"{field} must be a non-empty list of strings including {required}"], None
    names: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            return [f"{field}[{index}] must be a non-empty string"], None
        names.append(item.strip())
    errors: list[str] = []
    if len(names) != len(set(names)):
        errors.append(f"{field} contains duplicate entries")
    if required not in names:
        errors.append(f"{field} must include {required}")
    return errors, names


def _repo_names(dimensions: Any) -> list[str] | None:
    """Return unique non-empty repo name strings, or None if unusable."""
    if not isinstance(dimensions, dict):
        return None
    return _string_list(dimensions.get("repo"))


def _repo_error(index: int, dimensions: Any) -> str | None:
    """Return a specific dimensions.repo error, or None when the list is usable."""
    if not isinstance(dimensions, dict) or "repo" not in dimensions:
        return f"automations[{index}] trigger has no dimensions.repo"
    repos = dimensions.get("repo")
    if not isinstance(repos, list) or not repos:
        return f"automations[{index}] trigger has no dimensions.repo"
    names: list[str] = []
    for item in repos:
        if not isinstance(item, str) or not item.strip():
            return f"automations[{index}] trigger has no dimensions.repo"
        names.append(item.strip())
    if len(names) != len(set(names)):
        return f"automations[{index}] trigger dimensions.repo contains duplicate entries"
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
    provider_errors, providers = _catalog_list_errors(
        "catalog_providers_available",
        payload.get("catalog_providers_available"),
        "github",
    )
    errors.extend(provider_errors)
    type_errors, trigger_types = _catalog_list_errors(
        "github_trigger_types",
        payload.get("github_trigger_types"),
        "push_to_branch",
    )
    errors.extend(type_errors)

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
            normalized_id = task_id.strip()
            if normalized_id in seen:
                errors.append(f"duplicate taskId {normalized_id}")
            else:
                seen.add(normalized_id)
        name = item["name"]
        if not isinstance(name, str) or not name.strip():
            errors.append(f"automations[{index}].name must be a non-empty string")
        if not isinstance(item["isActive"], bool):
            errors.append(f"automations[{index}].isActive must be a bool")
        summary = item["prompt_summary"]
        if not isinstance(summary, str) or not summary.strip():
            errors.append(f"automations[{index}].prompt_summary must be a non-empty string")
        trigger = item["trigger"]
        if not isinstance(trigger, dict):
            errors.append(f"automations[{index}].trigger must be an object")
            continue
        missing_trigger = [key for key in REQUIRED_TRIGGER_KEYS if key not in trigger]
        if missing_trigger:
            errors.append(f"automations[{index}].trigger missing {missing_trigger}")
            continue
        provider = trigger.get("provider")
        provider_name = None
        if not isinstance(provider, str) or not provider.strip():
            errors.append(f"automations[{index}].trigger.provider must be a non-empty string")
        else:
            provider_name = provider.strip()
            if providers is not None and provider_name not in providers:
                errors.append(
                    f"automations[{index}].trigger.provider {provider_name} is not in catalog_providers_available"
                )
        trigger_type = trigger.get("trigger_type")
        if not isinstance(trigger_type, str) or not trigger_type.strip():
            errors.append(
                f"automations[{index}].trigger.trigger_type must be a non-empty string"
            )
        elif (
            provider_name == "github"
            and trigger_types is not None
            and trigger_type.strip() not in trigger_types
        ):
            errors.append(
                f"automations[{index}].trigger.trigger_type {trigger_type.strip()} is not in github_trigger_types"
            )
        repo_error = _repo_error(index, trigger.get("dimensions"))
        if repo_error:
            errors.append(repo_error)
    return errors
