"""Live connection audit against the Composio connection layer.

Queries COMPOSIO_MANAGE_CONNECTIONS (action=list) for every toolkit and
produces a structured report: active / initiated / failed counts, per-
account IDs, aliases, and identity info. Designed to be called from the
runner or standalone via the CLI.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .composio_client import ComposioClient


@dataclass
class AccountInfo:
    account_id: str
    status: str
    alias: str | None = None
    is_default: bool = False
    user_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolkitConnection:
    toolkit: str
    status: str
    accounts: list[AccountInfo] = field(default_factory=list)


@dataclass
class ConnectionReport:
    generated_at: str
    total_toolkits: int
    active: int
    initiated: int
    failed: int
    toolkits: list[ToolkitConnection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConnectionAuditor:
    """Audit Composio connections for a list of toolkit slugs."""

    def __init__(self, client: ComposioClient) -> None:
        self._client = client

    def audit(self, toolkits: list[str]) -> ConnectionReport:
        """List connections for each toolkit and build the report."""
        report = ConnectionReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_toolkits=len(toolkits),
            active=0,
            initiated=0,
            failed=0,
        )
        for tk in toolkits:
            try:
                result = self._client.executor(
                    "composio___COMPOSIO_MANAGE_CONNECTIONS",
                    {"toolkits": [{"name": tk, "action": "list"}]},
                )
            except Exception as exc:
                report.errors.append(f"{tk}: {exc}")
                continue

            data = result.get("data", result) if isinstance(result, dict) else {}
            tk_data = data.get(tk, {}) if isinstance(data, dict) else {}
            status = tk_data.get("status", "unknown")
            accounts = [
                AccountInfo(
                    account_id=a.get("id", ""),
                    status=a.get("status", "unknown"),
                    alias=a.get("alias"),
                    is_default=a.get("is_default", False),
                    user_info=a.get("user_info") or {},
                )
                for a in tk_data.get("accounts", [])
            ]
            conn = ToolkitConnection(toolkit=tk, status=status, accounts=accounts)
            report.toolkits.append(conn)
            if status == "active":
                report.active += 1
            elif status == "initiated":
                report.initiated += 1
            else:
                report.failed += 1
        return report


# The 15 toolkits audited in this session, in the order they were checked.
AUDITED_TOOLKITS = [
    "gmail", "googlecalendar", "googledocs", "googlesheets", "googledrive",
    "googlemeet", "googleslides", "outlook", "excel", "one_drive",
    "netlify_mcp", "cloudflare", "vercel", "github", "figma",
]
