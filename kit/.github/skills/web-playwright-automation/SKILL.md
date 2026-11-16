---
name: web-playwright-automation
description: Compile approved web cases into source-mapped Playwright tests and execute by XLSX, JSON or folder reference with stale-mapping protection.
---

# Source-mapped Playwright lifecycle

Use the initialized workspace README and scripts/automation.py, not arbitrary
model-authored shell/test code. Generated cases are not automatically approved.

1. Accept the kit's test-cases.xlsx, draft.json or containing run folder.
   `prepare` needs the companion draft.json/request.json; it checks workbook
   cells against JSON rather than guessing an arbitrary Excel schema.
   Legacy binary .xls needs conversion/import work; do not claim it is supported.
2. Obtain explicit case review approval and run `prepare --confirm-approved-cases`.
   It snapshots IDs, expected results and source hashes into a fresh automation
   run. It does NOT generate executable behavior from prose without a plan.
3. Use approved live browser tools or reviewed locator/action evidence to author
   plan.json using prompts/automate.txt. Record each source ID exactly once.
   Keep ALL source expected outcomes, including negative assertions. Do not
   omit unsupported cases, invent selectors, skip failures, add retries or
   weaken results. Surface blockers if this browser contract cannot express them.
4. Human approval covers locators, actions, controlled data, preconditions and
   complete business assertion coverage. It is an attestation, not automatic
   semantic validation. No mutations to real records or unsupported login flows.
5. Confirm the authorized application base URL in APP_BASE_URL (or --base-url)
   before `compile --confirm-approved-plan`. Compilation pins this target;
   never infer or reuse a production target from a document. The compiler creates an actual
   .spec.cjs file, constrained plan/runtime and playwright-mapping.json linking
   source workbook/JSON hashes, test IDs, references and compiled file hashes.
   Tests are deterministically compiled from the reviewed plan; identify the
   actual plan author separately rather than claiming the compiler is AI.
6. To execute when the user gives only an XLSX/JSON path or folder, use
   `run --source PATH`. Resolve the mapping; never select a test by similar name.
   No mapping means prepare/compile first; changed sources or scripts invalidate
   mappings. A different runtime application/base path also stops execution.
   Multiple matches require explicit --mapping. Preserve operator
   intent when selecting individual --case-id values.
7. Runtime APP_BASE_URL and controlled APP_DATA_* values come from the operator.
   Optional simple login uses APP_USERNAME/APP_PASSWORD without reading or
   printing them. Do not assume unattended SSO/MFA is supported.
8. Run only on the authorized test application. --evidence is opt-in because screenshots
   and authenticated traces may contain sensitive data; login tracing is off.
   Keep reports, evidence and runner logs private. No automatic dependency
   downloads, credential setup or network-policy changes.
9. Report real per-case outcomes with the source ID mapping and report paths.
   Failed/skipped/missing/retried cases must never be reported as passed.
   Source case documents remain draft/not-executed definitions; execution
   evidence is written separately, not silently backfilled as approval.

Legacy CRM_* environment aliases remain supported; conflicting aliases fail.
Unsupported widgets, mutations and advanced authentication need separate work.
