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
