"""Consistency checks for persisted inventory and automation snapshots."""

from pathlib import Path

from audit.inventory import automation_errors, inventory_errors, load_json

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "composio-meta-inventory.json"
AUTOMATIONS = ROOT / "data" / "automations.json"


def test_meta_inventory_counts_match_unique_slugs():
    errors = inventory_errors(load_json(INVENTORY))
    assert errors == []


def test_meta_inventory_records_duplicate_screen_row():
    payload = load_json(INVENTORY)
    assert payload["unique_slugs"] == 18
    assert payload["screen_rows"] == 19
    assert payload["duplicate_screen_entry"] == "COMPOSIO_WAIT_FOR_CONNECTION"
    assert payload["schemas_retrieved"] == len(payload["tools"])


def test_automations_snapshot_matches_count():
    errors = automation_errors(load_json(AUTOMATIONS))
    assert errors == []


def test_inventory_errors_flag_screen_row_counted_as_schemas():
    payload = {
        "meta_tools_total": 19,
        "schemas_retrieved": 19,
        "unique_slugs": 19,
        "tools": {"COMPOSIO_SEARCH_TOOLS": {"status": "live"}},
    }
    errors = inventory_errors(payload)
    assert any("schemas_retrieved" in error for error in errors)


def test_automation_errors_flag_count_mismatch():
    errors = automation_errors(
        {
            "count": 2,
            "automations": [],
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
        }
    )
    assert any("count" in error for error in errors)


def test_inventory_errors_require_unique_slugs():
    errors = inventory_errors(
        {
            "meta_tools_total": 1,
            "schemas_retrieved": 1,
            "tools": {"COMPOSIO_SEARCH_TOOLS": {"status": "live"}},
        }
    )
    assert any("unique_slugs is required" in error for error in errors)


def test_inventory_errors_reject_duplicate_that_does_not_add_a_row():
    errors = inventory_errors(
        {
            "meta_tools_total": 1,
            "schemas_retrieved": 1,
            "unique_slugs": 1,
            "screen_rows": 1,
            "duplicate_screen_entry": "COMPOSIO_SEARCH_TOOLS",
            "tools": {"COMPOSIO_SEARCH_TOOLS": {"status": "live"}},
        }
    )
    assert any("greater than the unique slug count" in error for error in errors)


def test_automation_errors_reject_non_dict_dimensions():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": "t",
                    "name": "n",
                    "isActive": True,
                    "prompt_summary": "p",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": None,
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo" in error for error in errors)


def test_inventory_errors_reject_bool_unique_slugs():
    errors = inventory_errors(
        {
            "meta_tools_total": 1,
            "schemas_retrieved": 1,
            "unique_slugs": True,
            "tools": {"COMPOSIO_SEARCH_TOOLS": {"status": "live"}},
        }
    )
    assert any("unique_slugs must be an int" in error for error in errors)


def test_automation_errors_reject_bool_count():
    errors = automation_errors(
        {
            "count": True,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": "t",
                    "name": "n",
                    "isActive": True,
                    "prompt_summary": "p",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": ["nietzsche-ubermensch/composio-audit-suite"]},
                    },
                }
            ],
        }
    )
    assert any("count True" in error for error in errors)


def test_automation_errors_reject_unhashable_task_id():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": {"id": "t"},
                    "name": "n",
                    "isActive": True,
                    "prompt_summary": "p",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": ["nietzsche-ubermensch/composio-audit-suite"]},
                    },
                }
            ],
        }
    )
    assert any("taskId must be a non-empty string" in error for error in errors)


def test_automation_errors_reject_blank_repo_name():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": "t",
                    "name": "n",
                    "isActive": True,
                    "prompt_summary": "p",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": [""]},
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo" in error for error in errors)


def test_automation_errors_reject_non_string_repo_entry():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": "t",
                    "name": "n",
                    "isActive": True,
                    "prompt_summary": "p",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": [1]},
                    },
                }
            ],
        }
    )
    assert any("entries must be non-empty strings" in error for error in errors)
    assert not any("has no dimensions.repo" in error for error in errors)
