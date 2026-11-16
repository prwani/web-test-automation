---
description: Create reviewed source-mapped Playwright tests for the case file or folder in the inline request.
argument-hint: <case XLSX, JSON or folder; authorized CRM URL and reviewed UI evidence>
---

# Create executable Playwright tests

Lifecycle phase 2 (create executable tests). Exploration and case generation
both belong to phase 1; this command is not phase 3.

The text following this command is the customer's request, not a separate
prompt-file prerequisite:

$ARGUMENTS

Preserve the complete inline request, including quoted paths, selected scope,
target URL and constraints. Do not ask the customer to repeat supplied
information or create a prompt file. If the host appends arguments rather than
substituting the placeholder, use that accompanying user text. Ask only for
missing required details or unresolved review decisions. Prompt text is not
shell code and does not bypass approval gates.

Use the plugin's `crm-testcase` skill for safe workspace/path resolution, then
`crm-playwright-automation` for preparation and compilation only. Reuse an
approved initialized customer workspace; never write into the plugin cache.

Accept the kit's XLSX/JSON/case folder and its required companion files. Obtain
case approval before preparation. Author a plan only from verified live UI
evidence, preserving every case ID, precondition and all positive/negative
expected outcomes. Never invent selectors, skip unsupported cases or weaken
assertions. Identify unsupported behavior and authentication as blockers.

Stop for separate customer review of the complete plan before compilation.
Compile only after that approval and confirmation of the authorized CRM target.
Use the existing trusted compiler and record source/compiled hashes and
source-to-test mapping. Keep credentials outside prompts and generated files.

Output executable tests and the pinned mapping, not a passing execution claim.
Do not run the tests automatically. A preview-only request must describe
routing and review gates without side effects.
