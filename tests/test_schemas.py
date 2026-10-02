"""Tests for the schema registry module."""

from audit.schemas import SchemaRegistry, ToolSchema


def test_validate_response_missing_key():
    reg = SchemaRegistry()
    reg.register(
        ToolSchema(
            toolkit="t",
            slug="s",
            description="demo",
            output_schema={"required": ["id", "name"]},
        )
    )
    errors = reg.validate_response("t", "s", {"id": 1})
    assert any("name" in e for e in errors)


def test_validate_response_ok():
    reg = SchemaRegistry()
    reg.register(
        ToolSchema(
            toolkit="t",
            slug="s",
            description="demo",
            output_schema={"required": ["id"]},
        )
    )
    assert reg.validate_response("t", "s", {"id": 1}) == []


def test_by_toolkit_filters():
    reg = SchemaRegistry()
    reg.register(ToolSchema(toolkit="a", slug="one", description=""))
    reg.register(ToolSchema(toolkit="b", slug="two", description=""))
    assert len(reg.by_toolkit("a")) == 1
