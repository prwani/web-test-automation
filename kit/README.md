# Web test automation kit

This kit prepares read-only browser observations, drafts traceable test cases,
and creates reviewed source-mapped Playwright tests. It supports
web applications, not native desktop or mobile applications. It is an initial
workflow, not a universal browser adapter or a certification of any product.
No application compatibility is implied by a local fixture test.

## Setup

Use Python 3.11+, Node.js 22/24 LTS and an organization-approved package
registry. For optional AI generation, install and authenticate GitHub Copilot
CLI under your organization's policy. From the kit workspace:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
npx --no-install playwright install chromium
node scripts\playwright-skill.cjs setup --confirm-install-skills
node scripts\playwright-skill.cjs check
```

Run setup only after approval to install dependencies and the official skill.
The helper requires `.web-test-workspace.json`, refuses an existing skill or
receipt, and installs the pinned upstream skill in
`.agents\skills\playwright-cli` using an isolated workspace-local staging
directory; it does not install a browser or touch global skills/config.
Check verifies the installed files and private `.local` receipt against the
installed package. For upgrades use a fresh initialized workspace; preserve
existing drafts. Plugin loading never installs or runs anything.

Read the installed `SKILL.md` and `references\test-generation.md`. Invoke the
local CLI with `node node_modules\@playwright\cli\playwright-cli.js`; set
`$env:NO_UPDATE_NOTIFIER = "1"` to avoid upstream update checks. CLI 0.1.23
includes Playwright/core 1.65.0-alpha-2026-10-30; the test runner remains
`@playwright/test` 1.64.1. Verify debug/attach compatibility in your environment;
this pinned pair was verified through authenticated seed/debug/attach browser
actions. After `attach tw-XXXX`, explicitly use `-s=tw-XXXX` for every subsequent
CLI command, including `resume`, `snapshot` and `close`; attachment does not
select the default session. Node 22/24 satisfies the dependencies' Node >=20.

Authorize the test application, test data, any browser tools and any AI
processing before use. Use controlled records and least privilege. Keep `.local`,
`runs`, reports, traces, credentials and browser state private and out of source
control. Enforce filesystem permissions appropriate to your operating system.

## Explore and capture

Prepare a task, without connecting to a browser or calling AI:

```powershell
node scripts\explore.cjs --url https://test.example.invalid --prompt "Explore the read-only search and clear controls." --out .local\exploration
```

Use `web-feature-explorer` and `web-feature-exploration` only in an approved
browser-tool-enabled host. If tools are unavailable, report the blocker.
Alternatively capture interactively in a fresh headed browser:

```powershell
node scripts\capture.cjs --url https://test.example.invalid --prompt "Explore the read-only search and clear controls." --out .local\observations.raw.json
```

Sign in manually, navigate to the authorized feature and type `SIGNED IN`.
Describe actual actions and observed outcomes; the captured accessibility
snapshot may contain sensitive text. This is human-guided, not autonomous.
The output uses the unchanged schemaVersion 1 observation format with `scope`,
`reviewed: false`, and unique `UI-nnn` observations (`title`, `actions`,
`outcome`, `evidence`). `url`, `scope`, `captureSelector`,
`authenticatedSelector`, `requireManualAuthConfirmation` and `steps` remain
the configuration fields; they have not been renamed or migrated.

Selector-configured capture also supports explicitly reviewed `click`, `fill`,
`press`, `visible`, `absent` and `snapshot` steps with `--allow-ui-actions`.
This flag is not authorization for mutations: the operator must ensure every
action is read-only. Optional simple login config references environment
variable names using `usernameEnv` and `passwordEnv`; never put values in the
config. Headless capture requires configured login; SSO/MFA is human-managed.
Never capture the login screen, export browser storage, or bypass identity.

## Review and generate

Manually sanitize the raw observation JSON and any document before AI access.
Retain observed facts and identifiers; remove secrets and personal data.
Review is an operator attestation, not automatic redaction:

```powershell
python scripts\cases.py review --input .local\observations.raw.json --output .local\observations.reviewed.json --confirm-sanitized
python scripts\cases.py generate --mode ui-only --observations .local\observations.reviewed.json --out runs\case-generation --confirm-approved-inputs --prepare-only
```

For `ui-brd`, provide `--brd` with a sanitized Word document; `ui-only` rejects
BRD input and never invents requirements. Review the prepared request and use
`web-testcase-generation` or an authorized Copilot CLI run (omit
`--prepare-only`) to produce `draft.json`. Then:

```powershell
python scripts\cases.py export --run runs\case-generation
```

The generated workbook, JSON and provenance remain drafts, not test results.
Check every expected outcome, citation, ambiguity and missing feature manually.

## Generate, register and execute

Approve the cases and pin the authorized target before preparing the native
workflow. Follow the generated task and the official skill's seed, debug/attach,
plan and generate steps. Review every locator, action, precondition, assertion,
seed, fixture and line of native code; explicitly approve the code before
registering. Native Playwright code runs with operator privileges: it is not
sandboxed and static checks do not prove safety or business coverage.

```powershell
$env:APP_BASE_URL = "https://test.example.invalid"
python scripts\official.py prepare --source runs\case-generation --out runs\automation --confirm-approved-cases
# Generate and review native tests and their manifest using the prepared task.
python scripts\official.py register --run runs\automation --tests runs\automation\manifest.json --confirm-approved-tests
python scripts\automation.py run --source runs\case-generation
```

The prepared task specifies the exact manifest schema and paths. Upstream
suggestions to edit specs or use `fixme` are overridden: no changed expected
business outcomes without approval, and no skips, fixme, only, retries,
mocking, stubs, API substitution or credential reads. No unrestricted
automatic healing: at most two observed locator/synchronization repairs, each
followed by a rerun; otherwise report the blocker. Actions may only operate on
approved read-only flows.
For simple login, pass `--login PATH` to preparation with reviewed CSS strings
`username`, `password`, `submit` and `authenticated` (a post-login-only control).
Credentials come only from environment variables. Non-read requests are blocked
even during sign-in unless explicitly listed as, for example,
`"requests": [{"method": "POST", "path": "/session"}]`. The path includes the
exact query string, if any; never include secrets. This exception is active only
during login and does not authorize business writes.
For the legacy constrained plan, `APP_DATA_<KEY>` supplies `{{KEY}}`
placeholders. `APP_USERNAME` and
`APP_PASSWORD` supply optional simple-login credentials locally. Do not assume
unattended SSO/MFA. `--base-url` may supply the target; if both it and
the environment URL are set they must agree. Execution requires `APP_BASE_URL`
matching the pinned mapping, including path. The runner sets `APP_APPROVED_BASE_URL`,
`APP_CASE_IDS`, `APP_RUN_DIR`, `APP_HEADED` and `APP_EVIDENCE` internally.

Legacy `CRM_*` environment aliases remain supported, including for previously
compiled mappings. If both aliases are present they must agree; conflicting
values stop the run. `--case-id` selects exact mapped IDs, and `--mapping`
disambiguates multiple mappings. Changed sources or compiled files are rejected.
The supported workbook must retain its companion `draft.json` and
`request.json`; arbitrary Excel schemas and legacy `.xls` require an importer.
Reports are separate from draft source documents. Retries are zero; failed,
skipped, missing or retried cases never count as passed. `--evidence` opts in
to private screenshots and traces only after login.

`scripts\automation.py prepare` and `compile` remain available for existing
constrained-plan integrations; `prompts\automate.txt` documents their legacy
schema. That deterministic compiler is not the official Playwright generator.

## Boundaries and verification

Explore only approved same-origin read/search/filter/navigation flows. Human
identity sign-in may use its legitimate identity provider, but execution does
not bypass cross-origin authentication. Business mutations, unsupported
widgets, advanced authentication and additional app-specific adapters remain
future capabilities requiring separate authorization and implementation.
No production changes are authorized. Native Playwright can express arbitrary
code, so operator review is essential. Run `npm test` for unit safeguards; `npm run test:browser` and
`npm run test:automation` require an installed browser and exercise controlled
local fixtures only.
