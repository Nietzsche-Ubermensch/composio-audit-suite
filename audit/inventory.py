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
    """Return stripped non-empty strings, or None if any entry is unusable."""
    if not isinstance(value, list) or not value:
        return None
    names: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        names.append(item.strip())
    return names


def _repo_names(dimensions: Any) -> tuple[list[str] | None, str | None]:
    """Return numeric GitHub repo ids, or None plus a dimensions.repo error.

    Automations requires the numeric id from automation_list_trigger_resources,
    not an owner/name slug. Padding is stripped before the digit and uniqueness
    checks so " 1402031134 " and "1402031134" are the same id.
    """
    if not isinstance(dimensions, dict) or "repo" not in dimensions:
        return None, "trigger has no dimensions.repo"
    names = _string_list(dimensions.get("repo"))
    if names is None:
        return None, "dimensions.repo entries must be non-empty strings"
    if len(names) != len(set(names)):
        return None, "dimensions.repo contains duplicate repo ids"
    if any(not name.isdigit() for name in names):
        return None, "dimensions.repo entries must be numeric GitHub repo ids"
    return names, None


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
    providers = _string_list(payload.get("catalog_providers_available"))
    if providers is None or "github" not in providers:
        errors.append("catalog_providers_available must include github")
    trigger_types = _string_list(payload.get("github_trigger_types"))
    if trigger_types is None or "push_to_branch" not in trigger_types:
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
        if not isinstance(provider, str) or not provider.strip():
            errors.append(f"automations[{index}].trigger.provider must be a non-empty string")
        trigger_type = trigger.get("trigger_type")
        if not isinstance(trigger_type, str) or not trigger_type.strip():
            errors.append(
                f"automations[{index}].trigger.trigger_type must be a non-empty string"
            )
        _repos, repo_error = _repo_names(trigger.get("dimensions"))
        if repo_error is not None:
            errors.append(f"automations[{index}] {repo_error}")
        provider_name = provider.strip() if isinstance(provider, str) else ""
        type_name = trigger_type.strip() if isinstance(trigger_type, str) else ""
        if provider_name and providers is not None and provider_name not in providers:
            errors.append(
                f"automations[{index}].trigger.provider {provider_name} is not in catalog_providers_available"
            )
        if type_name and trigger_types is not None and type_name not in trigger_types:
            errors.append(
                f"automations[{index}].trigger.trigger_type {type_name} is not in github_trigger_types"
            )
    return errors
