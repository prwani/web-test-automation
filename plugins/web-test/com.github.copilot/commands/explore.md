---
description: Explore the application features and navigation guidance supplied after this command.
argument-hint: <application URL, feature(s), optional navigation hints and work folder>
---

# Explore requested application features

Lifecycle phase 1 (generate test cases): exploration supplies its UI evidence.
This is not a separate numbered phase.

The text following this command is the user's request, not a separate
prompt-file prerequisite:

$ARGUMENTS

Preserve the complete inline request, including quoted paths, multiple features
and navigation hints. Do not ask the user to repeat supplied information
or create a prompt file. If the host appends arguments rather than substituting
the placeholder, use that accompanying user text. Ask only for missing required
details or unresolved access/processing approval. Never interpret prompt text
as shell code or consent to unrelated actions.

Use the plugin's `web-test` skill for safe workspace/path resolution, then
`web-feature-exploration` for this request. Resolve the real loaded skill
locations; do not write into the plugin cache or assume a plugin-root variable
is expanded in ordinary prompt text. A helper may write a local prompt file
internally to preserve multiline input; the user need not supply one.

Confirm authorized application access and permission for AI processing of visible data.
Use approved browser tools or the existing human-guided capture path. Task
preparation alone is not exploration. Human login handles SSO/MFA; never read
credentials or export authentication state. Restrict interactions to the
requested read/search/navigation scope; no record mutations.
Check and read the installed official playwright-cli skill and its
test-generation reference; use its seed/debug/attach mechanics where supported.
Arbitrary widgets, write operations and cross-origin authentication are not
implemented by this naming change; report unsupported behavior as a blocker.

Produce actual, unreviewed observations and explicit gaps. Do not automatically
generate cases, compile tests or execute them. A preview-only request must
describe the intended routing and missing prerequisites without side effects.
