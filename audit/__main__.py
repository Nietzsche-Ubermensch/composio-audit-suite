"""python -m audit entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .composio_client import ComposioClient, from_json_file
from .runner import AuditRunner


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Composio audit suite")
    parser.add_argument(
        "--catalog",
        type=str,
        help="Path to a static JSON catalog file (offline mode)",
    )
    parser.add_argument(
        "--toolkits",
        type=str,
        help="Comma-separated toolkit filter (e.g. github,gmail,vercel)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="audit-report.json",
        help="Where to write the JSON report (default: audit-report.json)",
    )
    args = parser.parse_args(argv)

    if args.catalog:
        client = from_json_file(args.catalog)
    else:
        print(
            "No --catalog provided. The live Composio MCP executor must be wired "
            "in by the host environment; pass --catalog <file> for offline runs.",
            file=sys.stderr,
        )
        sys.exit(2)

    runner = AuditRunner(client)
    tk_filter = (
        [t.strip() for t in args.toolkits.split(",") if t.strip()]
        if args.toolkits
        else None
    )
    report = runner.run(toolkit_filter=tk_filter)
    out = runner.write_report(report, args.output)
    print(f"Report written to {out}")
    print(f"Toolkits audited: {len(report['toolkits'])}")
    print(f"Tools discovered: {report['graph_summary'].get('tool_count', 0)}")
    print(f"Errors: {len(report['errors'])}")
    if report["errors"]:
        for err in report["errors"]:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
