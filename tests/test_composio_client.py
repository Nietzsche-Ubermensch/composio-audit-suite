"""Tests for the Composio client adapter."""

from audit.composio_client import ComposioClient, from_json_file


def test_search_tools_filters_by_query():
    client = from_json_file("data/sample-catalog.json")
    hits = client.search_tools(query="github")
    assert len(hits) == 4
    assert all(h["toolkit"] == "github" for h in hits)


def test_get_tool_schemas_returns_requested():
    client = from_json_file("data/sample-catalog.json")
    result = client.get_tool_schemas(["github___create_or_update_file"])
    schemas = result.get("schemas", result)
    assert "github___create_or_update_file" in schemas
    assert "owner" in schemas["github___create_or_update_file"]["input_schema"]["required"]


def test_list_toolkits():
    client = from_json_file("data/sample-catalog.json")
    tks = client.list_toolkits()
    assert len(tks) == 4
    assert {t["slug"] for t in tks} == {"github", "gmail", "vercel", "figma"}


def test_check_connections_filters():
    client = from_json_file("data/sample-catalog.json")
    conns = client.check_connections(["github", "figma"])
    assert set(conns.keys()) == {"github", "figma"}
    assert conns["github"]["active"] is True


def test_executor_error_propagates():
    client = ComposioClient(executor=lambda name, args: {"error": "boom"})
    assert client.search_tools("x") == []
