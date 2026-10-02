"""Tests for the end-to-end audit runner."""

from audit.composio_client import from_json_file
from audit.runner import AuditRunner


def test_full_run_produces_report():
    client = from_json_file("data/sample-catalog.json")
    runner = AuditRunner(client)
    report = runner.run()

    assert report["graph_summary"]["tool_count"] == 7
    assert report["schema_summary"]["registered_schemas"] == 7
    assert "github" in report["toolkits"]
    assert report["toolkits"]["github"]["tool_count"] == 4
    assert report["connection_status"]["github"]["active"] is True
    assert report["mermaid"].startswith("flowchart TD")
    assert report["errors"] == []


def test_run_with_toolkit_filter():
    client = from_json_file("data/sample-catalog.json")
    runner = AuditRunner(client)
    report = runner.run(toolkit_filter=["gmail"])
    assert set(report["toolkits"].keys()) == {"gmail"}
    assert report["graph_summary"]["tool_count"] == 1


def test_write_report_creates_file(tmp_path):
    client = from_json_file("data/sample-catalog.json")
    runner = AuditRunner(client)
    report = runner.run()
    out = runner.write_report(report, tmp_path / "out.json")
    assert out.exists()
    assert out.stat().st_size > 0
