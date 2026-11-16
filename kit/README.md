# Web test automation kit

This kit prepares read-only browser observations, drafts traceable test cases,
and compiles reviewed plans into source-mapped Playwright tests. It supports
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
npx playwright install chromium
```

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

## Compile and execute

Approve the cases, prepare a plan, review every locator, action, precondition
and business assertion, and explicitly approve the plan before compiling:

```powershell
python scripts\automation.py prepare --source runs\case-generation --out runs\automation --confirm-approved-cases
$env:APP_BASE_URL = "https://test.example.invalid"
python scripts\automation.py compile --run runs\automation --plan runs\automation\plan.json --confirm-approved-plan
python scripts\automation.py run --source runs\case-generation
```

The prepared task and `prompts\automate.txt` specify the constrained plan
schema. Do not invent locators, skip cases, weaken assertions, inject scripts,
or substitute APIs. Semantic coverage is a human approval, not something the
compiler proves. Plan actions may only operate on approved read-only flows.
`APP_DATA_<KEY>` supplies `{{KEY}}` placeholders, and `APP_USERNAME` and
`APP_PASSWORD` supply optional simple-login credentials locally. Do not assume
unattended SSO/MFA. `--base-url` may supply the compile target; if both it and
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

## Boundaries and verification

Explore only approved same-origin read/search/filter/navigation flows. Human
identity sign-in may use its legitimate identity provider, but execution does
not bypass cross-origin authentication. Business mutations, unsupported
widgets, advanced authentication and additional app-specific adapters remain
future capabilities requiring separate authorization and implementation.
No automatic crawler, arbitrary JavaScript injection or production changes are
provided. Run `npm test` for unit safeguards; `npm run test:browser` and
`npm run test:automation` require an installed browser and exercise controlled
local fixtures only.
