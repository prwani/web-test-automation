# Web test automation

An application-neutral foundation for AI-assisted **browser** test-case
generation and reviewed Playwright automation. Supply the web application's
features and navigation hints; ERP, banking and CRM are possible domains,
not built-in adapters or claims of validated compatibility.

The Copilot plugin follows three phases:

| Phase | Result |
|---|---|
| Explore and generate cases | Reviewed UI observations, draft Excel/JSON cases and requirement/UI traceability |
| Create executable tests | Official Playwright CLI generates native tests; review and register their source mapping |
| Execute mapped cases | Resolve a supported workbook, JSON or folder to approved tests; report actual per-case results |

Use **ui-only** for reviewed observations, or **ui-brd** for observations plus
an approved Word BRD. Unknown business rules remain questions or explicit
proposals, not facts inferred from the UI.

## Build and load

`kit` is the canonical runtime. `plugins\web-test` contains only the unique
Copilot wrapper. Specialist skills, embedded kit copies, integrity manifests
and ZIPs are generated into ignored `dist` output, not duplicated in Git.

```powershell
python scripts\build-distributions.py
copilot --plugin-dir ".\dist\web-test-plugin"
```

In the loaded Copilot session, put the request directly after a command:

```text
/web-test:explore Mode: ui-only. Application URL: https://test.example.invalid. Explore purchase-order search. Navigation: Procurement > Orders > Search. Work folder: "D:\Web Test Work\Orders". Read-only; stop before case generation.
/web-test:generate-cases Mode: ui-only. Use my reviewed observations to draft search cases and flag missing boundary-rule evidence.
/web-test:create-tests Use "runs\orders\test-cases.xlsx". Prepare an observed-locator plan for review; do not execute.
/web-test:run-tests Run the approved cases in "runs\orders" using its existing mapping. Do not capture screenshots or traces.
```

These are separate requests, not automatic approval of subsequent phases.
Missing required inputs or unresolved reviews stop the workflow. No separate
customer-authored prompt file is needed.

The initializer creates a fresh workspace and verifies bundled file hashes.
It installs nothing and performs no authentication or application access.
Use that workspace's README for dependency setup and the mapped workflow.
Node.js, Python, Playwright/Chromium and an authenticated compatible Copilot
host are operator-managed prerequisites. Use your organization's approved
package feeds. Browser-agent/MCP support depends on the chosen host.
After dependency approval, explicitly install and verify the actual official
skill in the initialized workspace:

```powershell
npm ci
node scripts\playwright-skill.cjs setup --confirm-install-skills
node scripts\playwright-skill.cjs check
```

No automatic or global skill installation occurs. The upstream skill and
references are local ignored dependencies, not vendored source. Follow its
seed/debug/attach/plan/generate mechanics together with the stricter workspace
rules. CLI 0.1.23 carries Playwright/core 1.65.0-alpha while the existing
test runner is 1.64.1. This pinned pair was verified through real seed/debug,
attach, authenticated resume and read-only browser actions; recheck after
dependency changes. See the kit
README for setup, target pinning and mapped execution.

## Current boundaries

- Intended for authorized read/search/navigation scenarios with controlled
  test data. Record writes, ERP posting and financial transactions are not
  supported by this initial generalization.
- The legacy constrained compiler remains available, but is not the official
  generator. Native Playwright code is not sandboxed and requires careful
  human review; no claim is made that all widgets/auth combinations work.
- Human-assisted authentication remains explicit. Never put credentials,
  authentication storage or production/customer data into model prompts.
- Only the kit's exported `.xlsx` and companion JSON/request format is
  supported, not arbitrary spreadsheet schemas or legacy binary `.xls`.
- Source/compiled hashes and the approved target are checked before execution.
  Missing, stale or ambiguous mappings are blockers. Structural validation
  does not establish semantic assertion coverage or prove an interaction safe.
- Cases and native code require separate review. No changed business outcomes
  without approval, skips/fixme/only, retries, mocks, stubs, API substitution
  or credential reads. At most two observed locator/synchronization repairs,
  each rerun, otherwise report the blocker. Screenshots and
  traces require explicit data approval and stay outside Git.

This is not a guarantee of automating every web application. There are no
native desktop/mobile adapters, bundled MCP servers, cloud services or
automatic dependency installs.

## Verified integration

On 2026-11-16, an initialized distribution installed and hash-verified the
actual official skill. An operator explored a controlled EspoCRM surrogate
through official CLI seed/debug/attach actions; a loaded-plugin Copilot
invocation used that skill and captured action code to assemble five native
tests with complete business assertions. This was not the legacy compiler
or a claim of fully autonomous exploration.

After explicit native-code and evidence approval, all five distinct search
cases passed: full name, leading prefix, no results, and Reset from matching
and unmatched states. Workbook, JSON and both folder references passed, with
selected-case execution and source-only lookup also verified: **25 passing
case executions, zero failed/skipped/retried cases**, 25 post-login screenshots,
25 traces and nine JSON/HTML report sets. Sources, generated specs, approvals,
hash receipts and evidence remain private, outside this repository. This
read-only surrogate result does not establish other application compatibility.

## Source checks

After installing the kit's locked dependencies from an approved feed:

```powershell
python -m unittest discover -s kit\tests -p "test_*.py"
python -m unittest discover -s scripts -p "test_*.py"
node --test kit\tests\capture.test.cjs kit\tests\explore.test.cjs kit\tests\playwright-skill.test.cjs
python scripts\build-distributions.py
node --test dist\web-test-plugin\tests\initialize.test.cjs dist\web-test-plugin\tests\commands.test.cjs
```

The native command-discovery check additionally needs an installed,
authenticated compatible Copilot CLI. Reusable regression tests and their
synthetic fixtures are source; local test runs and their outputs are not.

This repository intentionally excludes demo business documents, generated
examples, private evidence, credentials, infrastructure/account details and
installed dependencies. No license grant is supplied.
