"""Tests for the connection auditor."""

from audit.connection_audit import ConnectionAuditor, AUDITED_TOOLKITS
from audit.composio_client import ComposioClient


_CATALOG_RESPONSE = {
    "data": {
        "gmail": {
            "toolkit": "gmail", "status": "active",
            "accounts": [{"id": "gmail_1", "status": "active", "is_default": True,
                           "user_info": {"email": "a@b.com"}}],
        },
        "slack": {
            "toolkit": "slack", "status": "initiated", "accounts": [],
        },
        "notion": {
            "toolkit": "notion", "status": "failed", "accounts": [],
        },
    }
}


def test_audit_counts():
    client = ComposioClient(executor=lambda name, args: _CATALOG_RESPONSE)
    report = ConnectionAuditor(client).audit(["gmail", "slack", "notion"])
    assert report.total_toolkits == 3
    assert report.active == 1
    assert report.initiated == 1
    assert report.failed == 1


def test_audit_captures_account_details():
    client = ComposioClient(executor=lambda name, args: _CATALOG_RESPONSE)
    report = ConnectionAuditor(client).audit(["gmail"])
    tk = report.toolkits[0]
    assert tk.accounts[0].account_id == "gmail_1"
    assert tk.accounts[0].user_info["email"] == "a@b.com"
    assert tk.accounts[0].is_default is True


def test_audit_handles_executor_error():
    client = ComposioClient(executor=lambda name, args: (_ for _ in ()).throw(RuntimeError("boom")))
    report = ConnectionAuditor(client).audit(["gmail"])
    assert report.errors and "boom" in report.errors[0]
    assert report.active == 0


def test_audited_toolkits_list_has_fifteen():
    assert len(AUDITED_TOOLKITS) == 15
    assert "composio-audit-suite" not in AUDITED_TOOLKITS
