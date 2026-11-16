# Web test automation foundation

A curated browser-testing foundation with an existing CRM-oriented baseline,
not yet a general-purpose application testing solution. It provides three phases:
explore and generate reviewable cases; compile approved cases into Playwright
tests; and execute mapped tests against an explicitly authorized target.

`kit/` is the canonical runtime; `plugins/crm-testcase/` contains the Copilot
wrapper. Build both distributions with Python 3:

```shell
python scripts/build-distributions.py
```

Generated ZIPs and an unpacked plugin for testing are placed in `dist/` and are
not source artifacts. The plugin initializer copies the bundled kit to a fresh
workspace; it does not install dependencies or access a CRM. See the kit README
for usage and prerequisites. Package feeds must be selected according to your
organization's policy.

Limitations: the baseline remains CRM-specific; cases and plans require human
review and authorization; generated tests require observed selectors and
controlled data. It does not import arbitrary workbooks or guarantee business
coverage. It does not include credentials, source documents, execution evidence,
browser dependencies, or a hosted service. No license grant is supplied.
