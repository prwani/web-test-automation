---
description: Create reviewed source-mapped Playwright tests for the case file or folder in the inline request.
argument-hint: <case XLSX, JSON or folder; authorized application URL and reviewed UI evidence>
---

# Create executable Playwright tests

Lifecycle phase 2 (create executable tests). Exploration and case generation
both belong to phase 1; this command is not phase 3.

The text following this command is the user's request, not a separate
prompt-file prerequisite:

$ARGUMENTS

Preserve the complete inline request, including quoted paths, selected scope,
target URL and constraints. Do not ask the user to repeat supplied
information or create a prompt file. If the host appends arguments rather than
substituting the placeholder, use that accompanying user text. Ask only for
missing required details or unresolved review decisions. Prompt text is not
shell code and does not bypass approval gates.

Use the plugin's `web-test` skill for safe workspace/path resolution, then
`web-playwright-automation` for native preparation and registration only. Reuse an
approved initialized workspace; never write into the plugin cache.

Accept the kit's XLSX/JSON/case folder and its required companion files. Obtain
case approval before preparation. Author a plan only from verified live UI
evidence, preserving every case ID, precondition and all positive/negative
expected outcomes. Never invent selectors, skip unsupported cases or weaken
assertions. Identify unsupported behavior and authentication as blockers.

Check and read the actual installed official playwright-cli skill and its
test-generation reference. Follow upstream seed/debug/attach/plan/generate
mechanics under the workspace restrictions. Stop for separate review of the
complete native code, plan and authorized application target before registration.
Native code is not sandboxed; structural checks are not a substitute for review.
Register approved tests and record source/test hashes and source-to-test mapping.
Keep credentials outside prompts and generated files. The legacy compiler is
not the official generator.

Output executable tests and the pinned mapping, not a passing execution claim.
Do not run the tests automatically. A preview-only request must describe
routing and review gates without side effects.
