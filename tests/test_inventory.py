"""Consistency checks for persisted inventory and automation snapshots."""

from pathlib import Path

from audit.inventory import automation_errors, inventory_errors, load_json

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "composio-meta-inventory.json"
AUTOMATIONS = ROOT / "data" / "automations.json"


def _automation(task_id: str, repo: str = "1402031134") -> dict:
    return {
        "taskId": task_id,
        "name": "n",
        "isActive": True,
        "prompt_summary": "p",
        "trigger": {
            "provider": "github",
            "trigger_type": "push_to_branch",
            "dimensions": {"repo": [repo]},
        },
    }


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
    assert any("trigger has no dimensions.repo" in error for error in errors)


def test_automation_errors_reject_whitespace_task_id():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [_automation("  ")],
        }
    )
    assert any("taskId must be a non-empty string" in error for error in errors)


def test_automation_errors_reject_padded_duplicate_task_id():
    errors = automation_errors(
        {
            "count": 2,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [_automation("t"), _automation(" t ")],
        }
    )
    assert any("duplicate taskId t" in error for error in errors)
    assert any("must not have surrounding whitespace" in error for error in errors)


def test_automation_errors_reject_malformed_repo_token():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [_automation("t", repo="owner/")],
        }
    )
    assert any("trigger has no dimensions.repo" in error for error in errors)


def test_automation_errors_accept_numeric_repo_id_and_owner_name():
    errors = automation_errors(
        {
            "count": 2,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                _automation("a", repo="1402031134"),
                _automation("b", repo=" Nietzsche-Ubermensch/composio-audit-suite "),
            ],
        }
    )
    assert errors == []


def test_automation_errors_reject_non_decimal_digit_repo_id():
    errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [_automation("t", repo=chr(178))],
        }
    )
    assert any("trigger has no dimensions.repo" in error for error in errors)


def test_automation_errors_reject_dot_repo_segments_and_duplicate_tokens():
    dot_errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [_automation("t", repo="owner/..")],
        }
    )
    assert any("trigger has no dimensions.repo" in error for error in dot_errors)
    payload = _automation("t", repo="1402031134")
    payload["trigger"]["dimensions"]["repo"] = ["1402031134", " 1402031134 "]
    dup_errors = automation_errors(
        {
            "count": 1,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [payload],
        }
    )
    assert any("trigger has no dimensions.repo" in error for error in dup_errors)

def test_automation_errors_reject_zero_and_unreal_slugs_without_raising():
    errors = automation_errors(
        {
            "count": 3,
            "catalog_providers_available": ["github"],
            "github_trigger_types": ["push_to_branch"],
            "automations": [
                _automation("zero", repo="0"),
                _automation("slash", repo="owner/name/extra"),
                _automation("bad", repo="not a slug"),
            ],
        }
    )
    assert len(errors) == 3
    assert all("trigger has no dimensions.repo" in error for error in errors)


def test_inventory_module_is_not_a_placeholder():
    source = (ROOT / "audit" / "inventory.py").read_text(encoding="utf-8")
    assert "PLACEHOLDER" not in source
    assert "see-file" not in source
    assert "def automation_errors" in source
    assert "def _repo_token" in source

