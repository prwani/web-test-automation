---
name: crm-testcase
description: Coordinate CRM exploration, Excel/JSON case generation and approved source-mapped Playwright compilation/execution in an isolated customer workspace.
---

Load the plugin's `crm-testcase` skill and follow its workspace initialization,
path resolution and approval gates. Accept user-selected features, optional
navigation guidance and explicit ui-only or ui-brd mode.

Run helpers only from the initialized customer workspace. Never write customer
data, dependencies or credentials into the plugin installation. Browser/MCP
capability and authentication require customer setup; report missing tools.
Do not imply task preparation performs live exploration.

Use the specialist exploration/generation skills as appropriate; subagents are
optional and inherit only the explicit approved task, not new permissions.
If already generating in this host, use prepare-only plus validated export
instead of recursively starting a new orchestration agent. Preserve draft
case-document status and all safety/traceability requirements.

For runnable tests and execution, use crm-playwright-automation. Resolve the
user's XLSX/JSON/folder through verified mappings; never guess script names.
Separate case approval, observed-plan authoring, plan approval, compilation and
authorized execution. Report real per-case outcomes separately from draft case
definitions. Missing, stale or ambiguous mappings must stop execution.

Do not provision infrastructure, mutate CRM records, weaken assertions or
claim unexecuted cases passed. No model or host-specific tool list
is hardcoded; the host's existing permission decisions still apply.
