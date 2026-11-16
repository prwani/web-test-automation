---
description: Generate traceable Excel and JSON cases from the inline request and approved evidence.
argument-hint: <ui-only or ui-brd, reviewed observations, optional BRD and output scope>
---

# Generate draft CRM test cases

Lifecycle phase 1 (generate test cases), following exploration/review within
that same phase. Four commands do not mean four lifecycle phases.

The text following this command is the customer's request, not a separate
prompt-file prerequisite:

$ARGUMENTS

Preserve the complete inline request, including quoted paths, features and
navigation context. Do not ask the customer to repeat supplied information
or create a prompt file. If the host appends arguments rather than substituting
the placeholder, use that accompanying user text. Ask only for missing required
details or unresolved approval. Never interpret prompt text as shell code.

Use the plugin's `crm-testcase` skill for safe workspace/path resolution, then
`crm-testcase-generation`. Resolve real loaded skill locations and operate only
in the approved initialized customer workspace, never the plugin cache.

Require explicit ui-only or ui-brd mode and reviewed, sanitized observations.
ui-brd requires an approved Word BRD; ui-only forbids reading a BRD. If only a
CRM URL is supplied, explain the missing reviewed observations and route
exploration only after its access/data-processing approval; do not invent UI
evidence or silently change the requested mode.

Use the existing generation/validation/export helpers. When already acting as
the generator, use prepare-only plus validated export rather than recursively
launching another agent. Preserve business IDs, citations, assumptions and
generation provenance. Do not read credentials or embed them in model inputs.

Output Excel cases with traceability/review questions, case JSON and provenance
as draft/not-executed definitions. Do not compile or execute tests. A
preview-only request must describe routing and prerequisites without side effects.
