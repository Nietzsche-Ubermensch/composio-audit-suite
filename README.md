# Composio Audit Suite

Production-grade audit tooling for Composio-connected toolkits.

## What it does

- **Dependency graphs** — maps tool-to-tool dependencies (which tools consume outputs of which) and renders them as Mermaid flowcharts with topological ordering
- **Tool schemas** — pulls input/output schemas from the Composio catalog, normalizes them, and caches them
- **Response schemas** — validates live tool responses against registered output schemas, flagging missing required keys
- **Plan generator** — turns a goal into an ordered sequence of tool calls respecting the dependency graph, with forward-dependency rejection
- **Connection auditing** — checks which toolkits have active authenticated accounts
- **CI** — GitHub Actions runs the full test suite on every push and pull request

## Install

```bash
pip install -e ".[test]"
```

## Usage

Offline run against a static catalog:

```bash
python -m audit --catalog data/sample-catalog.json --output audit-report.json
```

Filter to specific toolkits:

```bash
python -m audit --catalog data/sample-catalog.json --toolkits github,gmail
```

## Architecture

```
audit/
  composio_client.py   # Composio MCP adapter (live + offline/JSON modes)
  dependency_graph.py   # Directed dependency graph + Mermaid rendering
  schemas.py            # Schema registry + response validation
  planner.py            # Execution plan generator
  runner.py             # End-to-end audit pipeline
  cli.py                # Command-line entry point
  __main__.py           # python -m audit
```

## Tests

```bash
python -m pytest tests/ -v
```

All modules are stdlib-only (no third-party runtime dependencies). Python 3.10+.
