---
description: Execute approved mapped cases using the Excel, JSON or folder reference supplied inline.
argument-hint: <case XLSX, JSON or folder; optional case IDs, mapping and evidence request>
---

# Execute approved mapped test cases

Lifecycle phase 3 (execute mapped cases), not phase 4. Exploration and case
generation both belong to phase 1; executable-test creation is phase 2.

The text following this command is the customer's request, not a separate
prompt-file prerequisite:

$ARGUMENTS

Preserve the complete inline request, including quoted paths, selected case
IDs, target restrictions and evidence choices. Do not ask the customer to
repeat supplied information or create a prompt file. If the host appends
arguments rather than substituting the placeholder, use that accompanying user
text. Ask only for missing runtime authorization, required values or an
ambiguous mapping choice. Never interpret prompt text as shell code.

Use the plugin's `crm-testcase` skill for safe workspace/path resolution, then
`crm-playwright-automation` for mapped execution. Reuse the approved initialized
workspace; never initialize into an existing folder or write into the plugin cache.

Resolve the supplied workbook, draft JSON, source folder or automation folder
through the existing mapping. Do not require the original BRD, feature prompt,
generation mode or generated spec filename again. Missing, stale or ambiguous
mappings stop execution; report the exact blocker instead of regenerating tests,
choosing the latest mapping or guessing a similarly named script.

Use the existing trusted runner. Verify source/compiled hashes and the runtime
CRM URL against the approved pinned target before browser launch. Respect
selected case IDs; never drop failed cases, add retries or weaken assertions.
Credentials come only from the approved local runtime environment, not this
prompt. Screenshots/traces require explicit evidence/data approval.

Report actual source-mapped outcomes and private evidence paths separately from
source definitions. A preview-only request must describe routing and checks
without browser launches, file changes or other side effects.
