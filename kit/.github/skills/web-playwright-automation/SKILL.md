---
name: web-playwright-automation
description: Generate reviewed official Playwright CLI tests and execute source-mapped web cases.
---

# Source-mapped Playwright lifecycle

Work only in an initialized workspace. Check the actual installed upstream skill
with `node scripts/playwright-skill.cjs check`; if absent, stop for permission
and follow the README's explicit dependency and skill setup. Read
`.agents/skills/playwright-cli/SKILL.md` and
`.agents/skills/playwright-cli/references/test-generation.md`. Use the upstream
seed, debug/attach, plan and native TypeScript generation mechanics. The local
CLI entrypoint is `node node_modules/@playwright/cli/playwright-cli.js`; use
the pinned local runner, not an unpinned network `npx` or global installation.
If debug/attach or the browser is unavailable, report the blocker.

1. Accept the kit's workbook, draft JSON or containing folder; preserve its
   companion files. Arbitrary Excel schemas and legacy `.xls` are unsupported.
   Obtain explicit case approval, then use `python scripts/official.py prepare`
   to snapshot source IDs, outcomes and authorized target. Do not infer the
   target from a document.
2. With approved access, AI processing and controlled data, explore through the
   seed test and attach workflow. Human login handles SSO/MFA. Do not read
   credential values, export storage or attach personal profiles. Use actual
   observed controls; read/search/navigation only, no business record mutation.
3. Generate native Playwright tests and a plan from the official workflow.
   Preserve every case ID, requirement reference, precondition and all positive
   and negative expected outcomes. Generated actions need explicit business
   assertions. Missing evidence and unsupported behavior are blockers.
4. Human review of native test code, target, actions, controlled data and
   complete assertions is essential. Native Playwright code is not sandboxed;
   registration and structural checks do not prove safety or semantic coverage.
   After explicit test approval, use `python scripts/official.py register` to
   pin source, tests and target to a mapping.
5. Execute file/folder requests with `python scripts/automation.py run --source
   PATH`, which resolves the appropriate mapped backend. Never guess a test
   filename or silently choose among mappings. Changed sources/tests or a
   different authorized runtime target must block execution. Respect exact case
   selections. Reports/evidence remain private and require data approval.
6. Report actual source-mapped per-case results; failed, skipped, missing or
   retried cases never count as passed. Draft definitions are not results.

Upstream instructions permitting spec edits or `fixme` are overridden: never
change expected business outcomes without approval; no skip, fixme, only,
retries, mocks, stubs, API substitution, or credential reads. No unrestricted
automatic healing: only observed locator/synchronization repairs, at most two,
with a rerun after each; otherwise report the blocker or application failure.

`scripts/automation.py prepare/compile` remains a legacy deterministic
constrained-plan compiler, not the official generator. Existing legacy mappings
remain supported. Neither native Playwright APIs nor this workflow imply that
all widgets or authentication combinations have been validated.
