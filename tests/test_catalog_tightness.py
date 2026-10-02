"""Catalog hygiene and repo-list errors added after the padded task id fix."""

from audit.inventory import automation_errors


def test_automation_errors_reject_padded_catalog_provider():
    errors = automation_errors(
        {
            "count": 0,
            "catalog_providers_available": [" github "],
            "github_trigger_types": ["push_to_branch"],
            "automations": [],
        }
    )
    assert any(
        "catalog_providers_available[0] must be a non-empty string" in error
        for error in errors
    )
    assert any("catalog_providers_available must include github" in error for error in errors)


def test_automation_errors_reject_padded_catalog_trigger_type():
    errors = automation_errors(
        {
            "count": 0,
            "catalog_providers_available": ["github", "github"],
            "github_trigger_types": ["push_to_branch", " pr_opened "],
            "automations": [],
        }
    )
    assert any("catalog_providers_available contains duplicate github" in error for error in errors)
    assert any(
        "github_trigger_types[1] must be a non-empty string" in error for error in errors
    )


def test_automation_errors_reject_empty_repo_list():
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
                        "dimensions": {"repo": []},
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo must be a non-empty list" in error for error in errors)
    assert not any("trigger has no dimensions.repo" in error for error in errors)


def test_automation_errors_reject_duplicate_repo_entry():
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
                        "dimensions": {"repo": ["1402031134", "1402031134"]},
                    },
                }
            ],
        }
    )
    assert any("dimensions.repo contains duplicate 1402031134" in error for error in errors)


def test_automation_errors_reject_padded_name():
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
    assert any("name must be a non-empty string" in error for error in errors)
