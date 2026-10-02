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


def test_inventory_errors_reject_whitespace_duplicate_screen_entry():
    errors = inventory_errors(
        {
            "meta_tools_total": 1,
            "schemas_retrieved": 1,
            "unique_slugs": 1,
            "screen_rows": 2,
            "duplicate_screen_entry": "   ",
            "tools": {"COMPOSIO_SEARCH_TOOLS": {"status": "live"}},
        }
    )
    assert any("duplicate_screen_entry must be a non-empty slug" in error for error in errors)


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
                        "dimensions": {"repo": [None]},
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo" in error for error in errors)


def test_automation_errors_reject_blank_name_and_non_bool_active():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": "t",
                    "name": "  ",
                    "isActive": 1,
                    "prompt_summary": "",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": ["nietzsche-ubermensch/composio-audit-suite"]},
                    },
                }
            ],
        }
    )
    assert any("name must be a non-empty string" in error for error in errors)
    assert any("prompt_summary must be a non-empty string" in error for error in errors)
    assert any("isActive must be a bool" in error for error in errors)


def test_automation_errors_reject_padded_task_id():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": " t ",
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


def test_automation_errors_reject_unknown_trigger_type():
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
                        "trigger_type": "not_a_real_event",
                        "dimensions": {"repo": ["nietzsche-ubermensch/composio-audit-suite"]},
                    },
                }
            ],
        }
    )
    assert any("trigger_type must be a github trigger type" in error for error in errors)


def test_automation_errors_reject_provider_outside_catalog():
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
                        "provider": "not-a-provider",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": ["nietzsche-ubermensch/composio-audit-suite"]},
                    },
                }
            ],
        }
    )
    assert any("provider must be a catalog provider" in error for error in errors)


def test_automation_errors_reject_blank_repo_name_explicitly():
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
                        "dimensions": {"repo": ["  "]},
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo entries must be non-empty strings" in error for error in errors)


def test_automation_errors_reject_padded_name_and_summary():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                {
                    "taskId": "t",
                    "name": " n ",
                    "isActive": True,
                    "prompt_summary": " p ",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": ["nietzsche-ubermensch/composio-audit-suite"]},
                    },
                }
            ],
        }
    )
    assert any("name must be a non-empty string" in error for error in errors)
    assert any("prompt_summary must be a non-empty string" in error for error in errors)


def test_automation_errors_reject_padded_catalog_entries():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github", " github"],
            "github_trigger_types": ["push_to_branch", " push_to_branch "],
            "automations": [
                {
                    "taskId": "t",
                    "name": "n",
                    "isActive": True,
                    "prompt_summary": "p",
                    "trigger": {
                        "provider": "github",
                        "trigger_type": "push_to_branch",
                        "dimensions": {"repo": ["1402031134"]},
                    },
                }
            ],
        }
    )
    assert any(
        "catalog_providers_available entries must be non-empty strings" in error
        for error in errors
    )
    assert any(
        "github_trigger_types entries must be non-empty strings" in error
        for error in errors
    )


def test_automation_errors_reject_owner_name_repo_slug():
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
                        "dimensions": {"repo": ["nietzsche-ubermensch/composio-audit-suite"]},
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo entries must be numeric repo ids" in error for error in errors)


def test_automation_errors_accept_numeric_repo_id():
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
                        "dimensions": {"repo": ["1402031134"]},
                    },
                }
            ],
        }
    )
    assert errors == []


def test_automation_errors_reject_non_list_repo():
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
                        "dimensions": {"repo": "1402031134"},
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo must be a non-empty list" in error for error in errors)


def test_automation_errors_reject_padded_trigger_type():
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
                        "trigger_type": " push_to_branch ",
                        "dimensions": {"repo": ["1402031134"]},
                    },
                }
            ],
        }
    )
    assert any("trigger_type must be a non-empty string" in error for error in errors)
