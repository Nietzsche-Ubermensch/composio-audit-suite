# Trigger Fix — What Was Wrong, What Was Fixed

## The mistake

I searched the Composio *app-tool* catalog (`COMPOSIO_SEARCH_TOOLS`) for trigger-creation tools. That catalog only returns per-app tools (Zendesk, PagerDuty, etc.) and never surfaces the Automations system. So I told you triggers didn't exist. They did. I was looking in the wrong layer.

## The fix

The trigger tools live under the **Automations** remote, not Composio:

- `automation_list_trigger_catalog` — lists every provider/type/dimension available to this account
- `automation_list_trigger_resources` — resolves GitHub owner/name to numeric repo IDs (required for `dimensions.repo`)
- `automation_create` — creates the automation with a `trigger` object
- `automation_list` / `automation_update` / `automation_pause` / `automation_delete` / `automation_run_now` / `automation_get_results` / `automation_validate`

## What is live right now

1. **composio-repo-push-monitor** (`b66a99d1-1884-41ed-bb65-cdede8fe99cf`) — fires on every push to `Nietzsche-Ubermensch/composio` (repo id `1386493327`). Reads the commits, reviews the code, opens a PR with fixes if anything is broken, reports back.
2. **composio-audit-suite-push-monitor** (`299c5ecc-b4ae-4814-ac29-a3cf09605169`) — same for `Nietzsche-Ubermensch/composio-audit-suite` (repo id `1402031134`).

Both are active, trigger-only (no schedule), and persist across chats.

## How to verify

- `automation_list` returns both with `isActive: true`
- Push anything to either repo and the automation fires
- `automation_get_results` with the taskId shows each run's output

## Composio meta-tool slugs

All 19 slugs from the Composio toolkit page have schemas retrievable via `COMPOSIO_GET_TOOL_SCHEMAS`. None are directly executable from this connector ("Cannot execute meta tool directly"). Their jobs are covered by the Automations tools and `COMPOSIO_MANAGE_CONNECTIONS`.
