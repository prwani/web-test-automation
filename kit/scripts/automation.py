"""Prepare, compile and run source-mapped Playwright tests from approved kit cases."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from openpyxl import load_workbook

from cases import ROOT, STATUS, read_json, sha, strings, text, validate_draft, write_json

TARGET_KINDS = {"css", "role", "label", "text"}
ASSERTIONS = {"expectVisible", "expectAbsent", "expectText", "expectValue", "expectCount"}
ACTIONS = {"goto", "click", "fill", "press"} | ASSERTIONS


def inside(path, parent):
    return Path(path).resolve().is_relative_to(Path(parent).resolve())


def app_url(value):
    if not isinstance(value, str) or not value.isascii() or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("Provide the approved APP_BASE_URL or --base-url as an ASCII URL without whitespace")
    parsed = urlsplit(value)
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
            or parsed.scheme not in {"https", "http"}
            or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})):
        raise ValueError("Approved application URL requires HTTPS (or loopback HTTP), no credentials, query or fragment")
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    port = parsed.port
    if port is not None and port != (443 if parsed.scheme == "https" else 80):
        host += f":{port}"
    return urlunsplit((parsed.scheme, host, parsed.path or "/", "", ""))


# Kept for callers of the original Python interface.
crm_url = app_url


def check_aliases(env):
    names = {"BASE_URL", "APPROVED_BASE_URL", "USERNAME", "PASSWORD", "CASE_IDS",
             "RUN_DIR", "EVIDENCE", "HEADED"}
    names.update(key[4:] for key in env if key.startswith(("APP_DATA_", "CRM_DATA_")))
    for key in names:
        app, legacy = f"APP_{key}", f"CRM_{key}"
        if app in env and legacy in env:
            left, right = env[app], env[legacy]
            if key in {"BASE_URL", "APPROVED_BASE_URL"}:
                left, right = app_url(left), app_url(right)
            if left != right:
                raise ValueError(f"Conflicting {app} and {legacy} environment variables")


def aliased(env, suffix):
    return env.get(f"APP_{suffix}", env.get(f"CRM_{suffix}"))


def source_cases(source):
    source = Path(source).resolve()
    if source.is_dir():
        source = source / ("test-cases.xlsx" if (source / "test-cases.xlsx").is_file() else "draft.json")
    if source.name not in {"test-cases.xlsx", "draft.json"}:
        raise ValueError("Use the kit's test-cases.xlsx, draft.json or containing run folder; arbitrary/legacy .xls schemas need an explicit importer")
    draft_path = source.parent / "draft.json"
    request_path = source.parent / "request.json"
    if not draft_path.is_file() or not request_path.is_file():
        raise ValueError("Preparation requires companion draft.json and request.json from the kit run; retain those with the workbook")
    draft, request = read_json(draft_path), read_json(request_path)
    validate_draft(request, draft)
    workbook_path = source.parent / "test-cases.xlsx"
    sources = [{"kind": "draft", "path": str(draft_path), "sha256": sha(draft_path)},
               {"kind": "generation-request", "path": str(request_path), "sha256": sha(request_path)}]
    if workbook_path.is_file():
        verify_workbook(workbook_path, draft)
        sources.append({"kind": "workbook", "path": str(workbook_path), "sha256": sha(workbook_path)})
    if not source.is_file():
        raise ValueError("Requested source file is missing")
    return draft, sources


def verify_workbook(path, draft):
    workbook = load_workbook(path, read_only=True, data_only=False)
    try:
        sheet = workbook["Test Cases"]
        if sheet.max_row != len(draft["cases"]) + 1 or sheet.max_column != 13:
            raise ValueError("Workbook and companion JSON differ in case/column count")
        rows = list(sheet.iter_rows())
        expected_headers = [
            "Test ID", "Title", "Category", "Priority", "Preconditions", "Steps", "Expected Result",
            "Expected Basis", "BRD Unit References", "UI References", "Assumptions", "Review Status", "Execution Status",
        ]
        if not rows or [c.value for c in rows[0]] != expected_headers:
            raise ValueError("Workbook is not the supported exported Test Cases schema")
        expected = [[c["id"], c["title"], c["category"], c["priority"], "\n".join(c["preconditions"]),
                     "\n".join(f"{i}. {s}" for i, s in enumerate(c["steps"], 1)), c["expectedResult"],
                     c["expectedBasis"], ", ".join(c["requirementRefs"]), ", ".join(c["observationRefs"]),
                     "\n".join(c["assumptions"]), STATUS, "Not Executed"] for c in draft["cases"]]
        actual = [[str(c.value) if c.value is not None else "" for c in row] for row in rows[1:]]
        if actual != expected or any(c.data_type == "f" for row in rows for c in row):
            raise ValueError("Workbook and companion JSON differ; reconcile/re-export approved cases before generating automation")
    finally:
        workbook.close()


def prepare(source, out, approved=False):
    if not approved:
        raise ValueError("Explicit --confirm-approved-cases is required; generated drafts are not automatically approved")
    draft, sources = source_cases(source)
    run = Path(out).resolve()
    if not inside(run, ROOT / "runs") or run == ROOT / "runs":
        raise ValueError("Automation output must be a fresh subdirectory of this workspace's runs folder")
    run.mkdir(parents=True, exist_ok=False)
    request = {
        "schemaVersion": 1, "scope": draft["scope"], "mode": draft["mode"],
        "cases": draft["cases"], "sources": sources,
        "instructions": "Preserve every source ID and expected result. Build a plan only from verified live UI locators. Report unsupported scenarios rather than skipping or weakening them.",
    }
    write_json(run / "automation-request.json", request)
    write_json(run / "preparation.json", {
        "requestSha256": sha(run / "automation-request.json"),
        "approval": "Operator explicitly confirmed cases reviewed for automation",
    })
    write_json(run / "plan.template.json", {
        "schemaVersion": 1, "login": None,
        "cases": [{"caseId": c["id"], "steps": []} for c in draft["cases"]],
    })
    prompt = (ROOT / "prompts" / "automate.txt").read_text(encoding="utf-8")
    (run / "agent-task.txt").write_text(prompt + f"\nRead {run / 'automation-request.json'}.\nWrite {run / 'plan.json'}.\n", encoding="utf-8")
    print(f"Prepared {run}; no executable plan, tests or execution created. Complete and review plan.json.")
    return run


def target(value):
    if not isinstance(value, dict) or not isinstance(value.get("by"), str) or value["by"] not in TARGET_KINDS:
        raise ValueError("Locator needs a supported by: css, role, label or text")
    expected = {"by", "value", "name"} if value["by"] == "role" else {"by", "value"}
    if set(value) != expected:
        raise ValueError("Locator fields must exactly match its supported shape")
    text(value["value"], "locator value", 3000)
    if value["by"] == "role":
        text(value["name"], "role accessible name", 3000)


def validate_plan(plan, cases):
    if not isinstance(plan, dict) or set(plan) != {"schemaVersion", "login", "cases"} or plan["schemaVersion"] != 1:
        raise ValueError("Plan needs exactly schemaVersion=1, login and cases")
    login = plan["login"]
    if login is not None:
        if not isinstance(login, dict) or set(login) != {"username", "password", "submit", "authenticated"}:
            raise ValueError("Login supports username/password/submit/authenticated locators only; credentials come from environment")
        for locator in login.values():
            target(locator)
    if not isinstance(plan["cases"], list):
        raise ValueError("Plan cases must be a list")
    ids = []
    for case in plan["cases"]:
        if not isinstance(case, dict) or set(case) != {"caseId", "steps"}:
            raise ValueError("Each plan case needs exactly caseId and steps")
        text(case["caseId"], "plan caseId")
        ids.append(case["caseId"])
        if not isinstance(case["steps"], list) or not 1 <= len(case["steps"]) <= 100:
            raise ValueError("Every source case needs 1 to 100 executable steps")
        checks = 0
        for step in case["steps"]:
            if not isinstance(step, dict) or not isinstance(step.get("action"), str) or step["action"] not in ACTIONS:
                raise ValueError("Unsupported plan action; no arbitrary code, skips, API substitution or retries")
            action = step["action"]
            fields = {"action", "path"} if action == "goto" else {"action", "target"}
            if action in {"fill", "press", "expectText", "expectValue", "expectCount"}:
                fields.add("value")
            if set(step) != fields:
                raise ValueError("Step fields must exactly match its action")
            if action == "goto":
                value = text(step["path"], "navigation path", 3000)
                if not value.startswith("/") or value.startswith("//") or "\\" in value or any(ord(c) < 32 for c in value):
                    raise ValueError("Navigation must be an origin-relative path; external URLs and script URLs are forbidden")
            else:
                target(step["target"])
            if action == "expectCount":
                if type(step["value"]) is not int or not 0 <= step["value"] <= 10000:
                    raise ValueError("Count expectations must be exact nonnegative integers")
            elif "value" in step:
                if action in {"fill", "expectValue"} and step["value"] == "":
                    pass
                else:
                    text(step["value"], "step value", 30000)
            checks += action in ASSERTIONS
        if not checks:
            raise ValueError("Every mapped case needs business assertions; navigation-only tests are not executable acceptance tests")
    expected = [c["id"] for c in cases]
    if len(set(ids)) != len(ids) or set(ids) != set(expected) or len(ids) != len(expected):
        raise ValueError("Plan must map every approved source test ID exactly once; no omitted, duplicate or invented cases")
    return plan


def prepared_request(run):
    if sha(run / "automation-request.json") != read_json(run / "preparation.json")["requestSha256"]:
        raise ValueError("Prepared automation request changed; start a fresh preparation")
    request = read_json(run / "automation-request.json")
    for source in request["sources"]:
        if sha(source["path"]) != source["sha256"]:
            raise ValueError("Source cases changed since preparation; regenerate the plan and mapping")
    return request


def compile_plan(run, plan_path, approved=False, base_url=None):
    if not approved:
        raise ValueError("Explicit --confirm-approved-plan is required after reviewing locators, test data, actions and all business assertions")
    run = Path(run).resolve()
    if not inside(run, ROOT / "runs"):
        raise ValueError("Compile only a prepared automation folder in this workspace's runs directory")
    request = prepared_request(run)
    plan = validate_plan(read_json(plan_path), request["cases"])
    check_aliases(os.environ)
    configured_url = aliased(os.environ, "BASE_URL")
    approved_url = app_url(base_url if base_url is not None else configured_url)
    if base_url is not None and configured_url is not None and approved_url != app_url(configured_url):
        raise ValueError("--base-url conflicts with the configured application base URL")
    names = ["compiled-plan.json", "cases.json", "runtime.cjs", "playwright.config.cjs", "tests/generated.spec.cjs"]
    if (run / "playwright-mapping.json").exists() or any((run / name).exists() for name in names):
        raise ValueError("Compiled output already exists; use a fresh preparation instead of overwriting evidence")
    (run / "tests").mkdir(exist_ok=True)
    write_json(run / "compiled-plan.json", plan)
    write_json(run / "cases.json", request["cases"])
    shutil.copyfile(ROOT / "templates" / "playwright-runtime.cjs", run / "runtime.cjs")
    shutil.copyfile(ROOT / "templates" / "playwright.config.cjs", run / "playwright.config.cjs")
    (run / "tests" / "generated.spec.cjs").write_text(
        "const { defineTests } = require('../runtime.cjs');\n"
        "defineTests(require('../compiled-plan.json'), require('../cases.json'));\n", encoding="utf-8")
    write_json(run / "playwright-mapping.json", {
        "schemaVersion": 1, "scope": request["scope"], "sources": request["sources"], "baseURL": approved_url,
        "requestSha256": sha(run / "automation-request.json"),
        "approval": "Operator explicitly confirmed plan reviewed; semantic coverage is human-reviewed, not automatically proven",
        "generator": "Deterministic Playwright compiler from reviewed locator/action/assertion plan",
        "files": {name: sha(run / name) for name in names},
        "cases": [{"caseId": c["id"], "title": f"{c['id']} | {c['title']}",
                   "spec": "tests/generated.spec.cjs", "requirementRefs": c["requirementRefs"],
                   "observationRefs": c["observationRefs"]} for c in request["cases"]],
    })
    print(f"Compiled {len(plan['cases'])} mapped Playwright cases in {run}; not executed.")
    return run / "playwright-mapping.json"


def mapping_matches(mapping_path, source):
    mapping = read_json(mapping_path)
    if source.is_file():
        role = {".xlsx": "workbook", ".json": "draft"}.get(source.suffix.lower())
        if role is None:
            raise ValueError("Execution source must be a kit .xlsx/.json file or mapped folder")
        return any(s["kind"] == role and s["sha256"] == sha(source) for s in mapping["sources"])
    if source.is_dir():
        if mapping_path.parent == source:
            for entry in mapping["sources"]:
                if not Path(entry["path"]).is_file() or sha(entry["path"]) != entry["sha256"]:
                    raise ValueError("Original source is missing or changed; provide the matching source file or regenerate mapping")
            return True
        entries = [s for s in mapping["sources"] if Path(s["path"]).parent == source]
        return bool(entries) and all(Path(s["path"]).is_file() and sha(s["path"]) == s["sha256"] for s in entries)
    raise ValueError("Requested source does not exist")


def resolve_mapping(source, explicit=None):
    source = Path(source).resolve()
    candidates = [Path(explicit).resolve()] if explicit else sorted((ROOT / "runs").rglob("playwright-mapping.json"))
    matches = []
    for path in candidates:
        if path.is_symlink():
            raise ValueError("Symlinked mappings are not supported")
        path = path.resolve()
        if not inside(path, ROOT / "runs"):
            raise ValueError("Use a mapping inside this workspace's runs directory")
        if mapping_matches(path, source):
            matches.append(path)
    if not matches:
        raise ValueError("No matching mapping: source may be changed or not yet compiled. Prepare/compile first; never guess a script")
    if len(matches) != 1:
        raise ValueError("Multiple mappings match this source; specify the intended --mapping explicitly")
    return matches[0]


def verify_mapping(path):
    mapping = read_json(path)
    run = path.parent
    expected_names = {"compiled-plan.json", "cases.json", "runtime.cjs", "playwright.config.cjs", "tests/generated.spec.cjs"}
    if mapping.get("schemaVersion") != 1 or set(mapping.get("files", {})) != expected_names:
        raise ValueError("Invalid compiled mapping file set")
    app_url(mapping.get("baseURL"))
    for name, digest in mapping["files"].items():
        if not inside(run / name, run) or (run / name).is_symlink() or sha(run / name) != digest:
            raise ValueError("Compiled plan/script/config changed; recompile approved cases in a fresh folder")
    if sha(run / "automation-request.json") != mapping["requestSha256"]:
        raise ValueError("Mapped request changed")
    cases = read_json(run / "cases.json")
    validate_plan(read_json(run / "compiled-plan.json"), cases)
    request = read_json(run / "automation-request.json")
    expected_cases = [{"caseId": c["id"], "title": f"{c['id']} | {c['title']}",
                       "spec": "tests/generated.spec.cjs", "requirementRefs": c["requirementRefs"],
                       "observationRefs": c["observationRefs"]} for c in cases]
    if mapping["cases"] != expected_cases or request["cases"] != cases or request["sources"] != mapping["sources"]:
        raise ValueError("Mapping does not match the compiled source cases")
    return mapping


def report_cases(report, selected):
    specs = []

    def visit(suite):
        specs.extend(suite.get("specs", []))
        for child in suite.get("suites", []):
            visit(child)

    visit(report)
    outcome = []
    for case in selected:
        matching = [s for s in specs if s["title"] == case["title"]]
        tests = matching[0].get("tests", []) if len(matching) == 1 else []
        results = tests[0].get("results", []) if len(tests) == 1 else []
        status = results[0]["status"] if len(results) == 1 else "missing-or-retried"
        outcome.append({**case, "status": status, "durationMs": results[0].get("duration", 0) if len(results) == 1 else 0})
    if len(specs) != len(selected):
        raise ValueError("Playwright discovered a different test set than the selected source mapping")
    return outcome


def execute(source, explicit=None, case_ids=None, evidence=False, headed=False):
    mapping_path = resolve_mapping(source, explicit)
    if read_json(mapping_path).get("engine") == "playwright-cli":
        from official import execute as execute_official
        return execute_official(source, explicit=mapping_path, case_ids=case_ids,
                                evidence=evidence, headed=headed)
    mapping = verify_mapping(mapping_path)
    check_aliases(os.environ)
    if app_url(aliased(os.environ, "BASE_URL")) != app_url(mapping["baseURL"]):
        raise ValueError("Runtime application target differs from the approved mapped base URL; review/recompile for the intended application before execution")
    approved = aliased(os.environ, "APPROVED_BASE_URL")
    if approved is not None and app_url(approved) != app_url(mapping["baseURL"]):
        raise ValueError("Configured approved base URL differs from the source mapping")
    selected = mapping["cases"]
    if case_ids:
        strings(case_ids, "selected case IDs", allow_empty=False)
        if not set(case_ids) <= {c["caseId"] for c in selected}:
            raise ValueError("Selected case IDs are not in this source mapping")
        selected = [c for c in selected if c["caseId"] in case_ids]
    cli = ROOT / "node_modules" / "@playwright" / "test" / "cli.js"
    if not cli.is_file() or not shutil.which("node"):
        raise ValueError("Install the workspace's locked Node/Playwright dependencies and browser before execution; no automatic download is attempted")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output = mapping_path.parent / "executions" / stamp
    output.mkdir(parents=True)
    env = dict(os.environ)
    # Older pinned runtimes and configs read CRM_*; expose matching aliases to both generations.
    for key in list(env):
        if key.startswith(("APP_DATA_", "CRM_DATA_")):
            suffix = key[4:]
            env[f"APP_{suffix}"] = env[f"CRM_{suffix}"] = aliased(env, suffix)
    for suffix in ("BASE_URL", "USERNAME", "PASSWORD"):
        value = aliased(env, suffix)
        if value is not None:
            env[f"APP_{suffix}"] = env[f"CRM_{suffix}"] = value
    internal = {"APPROVED_BASE_URL": mapping["baseURL"], "RUN_DIR": str(output),
                "CASE_IDS": json.dumps([c["caseId"] for c in selected]),
                "EVIDENCE": "1" if evidence else "0", "HEADED": "1" if headed else "0"}
    for suffix, value in internal.items():
        env[f"APP_{suffix}"] = env[f"CRM_{suffix}"] = value
    command = ["node", str(cli), "test", "--config", str(mapping_path.parent / "playwright.config.cjs")]
    with (output / "runner.log").open("w", encoding="utf-8") as log:
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=60 + len(selected) * 50, check=False)
        except subprocess.TimeoutExpired as error:
            write_json(output / "execution-summary.json", {
                "status": "Runner timeout - no passing outcome claimed", "mappingSha256": sha(mapping_path),
                "caseIds": [c["caseId"] for c in selected],
            })
            raise ValueError(f"Playwright timed out; inspect private evidence in {output}") from error
    report_path = output / "playwright-results.json"
    if not report_path.is_file():
        raise ValueError(f"Playwright produced no JSON report; inspect private {output / 'runner.log'}")
    outcomes = report_cases(read_json(report_path), selected)
    passed = result.returncode == 0 and all(c["status"] == "passed" for c in outcomes)
    write_json(output / "execution-summary.json", {
        "schemaVersion": 1, "status": "passed" if passed else "failed",
        "source": str(Path(source).resolve()), "mappingSha256": sha(mapping_path),
        "sources": mapping["sources"], "compiledFiles": mapping["files"], "cases": outcomes,
        "baseURL": mapping["baseURL"],
        "report": "playwright-results.json", "htmlReport": "html/index.html",
        "evidenceRequested": evidence,
    })
    print(f"{sum(c['status'] == 'passed' for c in outcomes)}/{len(outcomes)} mapped cases passed; report: {output / 'execution-summary.json'}")
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description="Compile and execute mapped Playwright cases from the kit's XLSX/JSON/folder outputs")
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--source", type=Path, required=True)
    prep.add_argument("--out", type=Path, required=True)
    prep.add_argument("--confirm-approved-cases", action="store_true")
    compile_cmd = commands.add_parser("compile")
    compile_cmd.add_argument("--run", type=Path, required=True)
    compile_cmd.add_argument("--plan", type=Path, required=True)
    compile_cmd.add_argument("--confirm-approved-plan", action="store_true")
    compile_cmd.add_argument("--base-url", help="Approved application URL; otherwise use APP_BASE_URL (legacy CRM_BASE_URL also supported)")
    run = commands.add_parser("run")
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--mapping", type=Path)
    run.add_argument("--case-id", action="append")
    run.add_argument("--evidence", action="store_true")
    run.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.source, args.out, args.confirm_approved_cases)
        elif args.command == "compile":
            compile_plan(args.run, args.plan, args.confirm_approved_plan, args.base_url)
        else:
            return execute(args.source, args.mapping, args.case_id, args.evidence, args.headed)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
