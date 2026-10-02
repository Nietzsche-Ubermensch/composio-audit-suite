"""Guards for repo-token validation that must reject without raising."""

from audit.inventory import automation_errors


def _payload(repo):
    return {
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
                    "dimensions": {"repo": [repo]},
                },
            }
        ],
    }


def test_non_string_repo_token_is_rejected_without_raising():
    errors = automation_errors(_payload(1402031134))
    assert any("dimensions.repo" in error for error in errors)


def test_git_suffix_is_not_a_real_repo_slug():
    errors = automation_errors(_payload("Nietzsche-Ubermensch/composio-audit-suite.git"))
    assert any("dimensions.repo" in error for error in errors)
