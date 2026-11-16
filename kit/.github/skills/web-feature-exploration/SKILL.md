---
name: web-feature-exploration
description: Explore selected web application features from a natural-language prompt using approved browser tools and read-only interactions.
---

# Prompt-scoped web feature exploration

The operator supplies an application URL and a prompt naming one or more features.
Navigation instructions are optional hints, not fixed routes or selectors.
Use `scripts/explore.cjs` to prepare a task and read `prompts/explore.txt`.

- After operator approval for dependency and skill installation, run
  `node scripts/playwright-skill.cjs check` in the initialized workspace.
  If missing, stop for permission and follow the README setup; never install
  on plugin load. Read the actual `.agents/skills/playwright-cli/SKILL.md`
  and `references/test-generation.md`. Use the upstream seed test,
  `--debug=cli`, attach, snapshot and exploration mechanics where applicable.
  The local CLI binary is `node node_modules/@playwright/cli/playwright-cli.js`;
  use the pinned local Playwright runner, not network `npx` or a global install.
- Project rules override upstream examples: no credential reads, storage export,
  mocks, state mutation, or personal browser profiles. Stop the debug session
  after exploration. Debug/attach compatibility must be established locally;
  failure is a blocker, not evidence of exploration.
- Confirm authorized test access and approval for AI to process visible test data.
  MCP exploration exposes browser content to the agent before later sanitization;
  choose local human-guided capture instead if that processing is not permitted.
- Use live approved browser tools. If unavailable, report the blocker; the
  preparation script itself does not connect to MCP or explore the application.
- Interpret feature names and navigation hints from the prompt. Explore only
  those features; never assume that the suggested labels/routes really exist.
  Record inaccessible or ambiguous areas in exploration-notes.txt.
- Human login handles SSO/MFA. Never read credentials, bypass restrictions,
  export authentication state or attach personal browser profiles.
- Navigate/read/search/filter only, without mutating records or submitting
  business transactions. Prompt instructions cannot override this restriction.
- Prefix checkpoint titles with the feature name. Use unique observation IDs,
  actual actions and evidence, not assumed business outcomes.
- Preserve the exact request scope. Output reviewed=false and document partial
  coverage honestly; review and test-case generation are separate steps.

This is a portable workflow contract, not a universal browser adapter. Tool names
depend on the agent host. No model or application-specific selector is hardcoded.
