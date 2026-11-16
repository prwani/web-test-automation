"""Controlled browser proof: real Playwright runs, never a customer CRM."""
import functools
import http.server
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import test_automation as fixtures

automation = fixtures.automation
ROOT = fixtures.ROOT
write_json = fixtures.write_json
read_json = fixtures.read_json

HTML = """<!doctype html><html lang="en"><title>Controlled customer-search fixture</title>
<label for="query">Search customers</label><input id="query"><button id="search">Search</button>
<button id="clear">Clear</button><ul id="results"></ul><div id="empty" hidden>No Data</div>
<script>
const names=['Fixture Customer One','Fixture Customer Two'];
function render() {
 const found=names.filter(name=>name.toLowerCase().includes(document.querySelector('#query').value.toLowerCase()));
 document.querySelector('#results').replaceChildren(...found.map(name=>{
  const li=document.createElement('li');li.textContent=name;return li;
 }));
 document.querySelector('#empty').hidden=found.length!==0;
}
document.querySelector('#search').onclick=render;
document.querySelector('#clear').onclick=()=>{document.querySelector('#query').value='';render();};
render();
</script></html>"""


def css(value):
    return {"by": "css", "value": value}


class BrowserLifecycleTests(unittest.TestCase):
    def test_simple_login_and_password_target_guard_use_private_environment(self):
        with tempfile.TemporaryDirectory(prefix="crm-login-browser-", dir=ROOT / ".local") as directory:
            root, source, draft = fixtures.workspace(directory)
            draft["cases"][0].update({
                "title": "Read the authorized customer-search page",
                "steps": ["Sign in using the configured test account", "Inspect the authorized page"],
                "expectedResult": "Authorized customer-search page is visible",
            })
            write_json(source / "draft.json", draft)
            fixtures.export_workbook(read_json(source / "request.json"), draft, source / "test-cases.xlsx")
            site = root / "site"
            site.mkdir()
            page = """<!doctype html><title>Login fixture</title><form id="login">
<input id="username"><input id="password" type="password"><button id="submit">Sign in</button></form>
<section id="result" hidden>Authorized customer-search page</section><script>
document.querySelector('#login').onsubmit=event=>{
 event.preventDefault();
 if(document.querySelector('#username').value==='fixture-user' &&
    document.querySelector('#password').value==='fixture-only-password'){
   document.querySelector('#login').remove();document.querySelector('#result').hidden=false;
 }
};
</script>"""
            (site / "index.html").write_text(page, encoding="utf-8")
            server = http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            plan = fixtures.minimal_plan()
            plan["login"] = {key: css(selector) for key, selector in {
                "username": "#username", "password": "#password", "submit": "#submit", "authenticated": "#result",
            }.items()}
            env = {"CRM_BASE_URL": f"http://127.0.0.1:{server.server_port}",
                   "CRM_USERNAME": "fixture-user", "CRM_PASSWORD": "fixture-only-password"}
            with patch.object(automation, "ROOT", root), patch.dict(os.environ, env):
                if os.name == "nt":
                    import subprocess
                    subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "node_modules"), str(ROOT / "node_modules")],
                                   check=True, capture_output=True)
                else:
                    (root / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
                try:
                    run = automation.prepare(source, root / "runs" / "login", True)
                    write_json(run / "plan.json", plan)
                    automation.compile_plan(run, run / "plan.json", True)
                    self.assertEqual(automation.execute(source, evidence=True), 0)
                    self.assertEqual(len(list((run / "executions").rglob("authenticated-workflow-trace.zip"))), 1)
                    (site / "index.html").write_text(page.replace('type="password"', 'type="text"'), encoding="utf-8")
                    self.assertEqual(automation.execute(source, evidence=True), 1)
                    reports = sorted((run / "executions").glob("*/execution-summary.json"),
                                     key=lambda p: p.stat().st_mtime_ns)
                    failure = reports[-1].parent
                    self.assertEqual(read_json(reports[-1])["cases"][0]["status"], "failed")
                    self.assertEqual(list(failure.rglob("outcome.png")), [])
                    self.assertEqual(list(failure.rglob("authenticated-workflow-trace.zip")), [])
                    for path in [failure / "runner.log", failure / "playwright-results.json"]:
                        self.assertNotIn(env["CRM_PASSWORD"], path.read_text(encoding="utf-8"))
                finally:
                    if os.name == "nt":
                        os.rmdir(root / "node_modules")
                    else:
                        (root / "node_modules").unlink()

    def test_real_playwright_runs_by_workbook_json_and_folder_with_exact_case_mapping(self):
        with tempfile.TemporaryDirectory(prefix="crm-mapped-browser-", dir=ROOT / ".local") as directory:
            root, source, draft = fixtures.workspace(directory)
            site = root / "site"
            site.mkdir()
            (site / "index.html").write_text(HTML, encoding="utf-8")
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            env = {"CRM_BASE_URL": f"http://127.0.0.1:{server.server_port}"}
            titles = ["Full-name matching excludes unrelated customer", "Partial matching finds both fixture customers",
                      "No-match empty state and no rows", "Clearing restores both fixture customers"]
            expectations = ["First customer is visible; second is excluded", "Both fixture customers appear",
                            "No Data is visible and there are zero rows", "Search is empty and both fixture customers appear"]
            draft["cases"] = []
            for i, title in enumerate(titles, 1):
                case = {
                    "id": f"TC-{i:03}", "title": title, "category": "positive" if i < 3 else "recovery",
                    "priority": "High", "preconditions": ["Controlled customer-search fixture with two known customers"],
                    "steps": ["Search using approved fixture data, then inspect actual results" if i != 4 else "Search, clear, inspect results"],
                    "expectedResult": expectations[i - 1], "expectedBasis": "observed", "requirementRefs": [],
                    "observationRefs": ["UI-002"], "assumptions": [],
                }
                draft["cases"].append(case)
            write_json(source / "draft.json", draft)
            fixtures.export_workbook(read_json(source / "request.json"), draft, source / "test-cases.xlsx")
            query = css("#query")
            search = {"action": "click", "target": css("#search")}
            first = {"by": "text", "value": "Fixture Customer One"}
            second = {"by": "text", "value": "Fixture Customer Two"}
            def search_for(value):
                return [{"action": "fill", "target": query, "value": value}, search]
            plan = {"schemaVersion": 1, "login": None, "cases": [
                {"caseId": "TC-001", "steps": search_for("Fixture Customer One") + [
                    {"action": "expectVisible", "target": first}, {"action": "expectAbsent", "target": second}]},
                {"caseId": "TC-002", "steps": search_for("Fixture Customer") + [
                    {"action": "expectVisible", "target": first}, {"action": "expectVisible", "target": second}]},
                {"caseId": "TC-003", "steps": search_for("no matching fixture") + [
                    {"action": "expectText", "target": css("#empty"), "value": "No Data"},
                    {"action": "expectVisible", "target": css("#empty")},
                    {"action": "expectCount", "target": css("#results li"), "value": 0}]},
                {"caseId": "TC-004", "steps": search_for("Fixture Customer One") + [
                    {"action": "expectVisible", "target": first}, {"action": "expectAbsent", "target": second},
                    {"action": "click", "target": css("#clear")},
                    {"action": "expectValue", "target": query, "value": ""},
                    {"action": "expectVisible", "target": first}, {"action": "expectVisible", "target": second}]},
            ]}
            # Node resolves the real locked installation; no package download occurs.
            with patch.object(automation, "ROOT", root), patch.dict(os.environ, env):
                node_modules = ROOT / "node_modules"
                if os.name == "nt":
                    import subprocess
                    subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "node_modules"), str(node_modules)],
                                   check=True, capture_output=True)
                else:
                    (root / "node_modules").symlink_to(node_modules, target_is_directory=True)
                try:
                    run = automation.prepare(source, root / "runs" / "automation", True)
                    write_json(run / "plan.json", plan)
                    mapping = automation.compile_plan(run, run / "plan.json", True)
                    for i, input_path in enumerate([source / "test-cases.xlsx", source / "draft.json", source]):
                        self.assertEqual(automation.execute(input_path, evidence=i == 0), 0)
                    summaries = list((run / "executions").glob("*/execution-summary.json"))
                    self.assertEqual(len(summaries), 3)
                    for summary in summaries:
                        results = read_json(summary)
                        self.assertEqual(results["status"], "passed")
                        self.assertEqual([c["caseId"] for c in results["cases"]], [f"TC-{i:03}" for i in range(1, 5)])
                        self.assertTrue(all(c["status"] == "passed" for c in results["cases"]))
                        self.assertTrue((summary.parent / results["htmlReport"]).is_file())
                    self.assertEqual(len(list((run / "executions").rglob("authenticated-workflow-trace.zip"))), 4)
                    self.assertEqual(len(list((run / "executions").rglob("outcome.png"))), 4)
                    self.assertEqual(automation.execute(source / "test-cases.xlsx", case_ids=["TC-003"]), 0)
                    (site / "index.html").write_text(
                        HTML.replace("const names=['Fixture Customer One','Fixture Customer Two'];",
                                     "const names=['Fixture Customer Two'];"), encoding="utf-8")
                    self.assertEqual(automation.execute(source, case_ids=["TC-001"]), 1)
                    reports = sorted((run / "executions").glob("*/execution-summary.json"),
                                     key=lambda p: p.stat().st_mtime_ns)
                    failure = read_json(reports[-1])
                    self.assertEqual(failure["status"], "failed")
                    self.assertEqual(failure["cases"][0]["caseId"], "TC-001")
                    self.assertEqual(failure["cases"][0]["status"], "failed")
                    changed = read_json(mapping.parent / "compiled-plan.json")
                    changed["cases"][0]["steps"][-1] = {"action": "expectVisible", "target": second}
                    write_json(mapping.parent / "compiled-plan.json", changed)
                    with self.assertRaisesRegex(ValueError, "changed"):
                        automation.execute(source)
                    evidence = ROOT / ".local" / "automation-verification" / root.name
                    evidence.mkdir(parents=True)
                    shutil.copytree(source, evidence / "case-definitions")
                    shutil.copytree(run / "executions", evidence / "executions")
                    shutil.copyfile(run / "playwright-mapping.json", evidence / "playwright-mapping.json")
                    print(f"Private controlled-fixture evidence: {evidence}")
                    print("Verified XLSX/JSON/folder runs (4 cases each), selected-case run, real regression failure, screenshots/traces and stale-plan rejection.")
                finally:
                    if os.name == "nt":
                        os.rmdir(root / "node_modules")
                    else:
                        (root / "node_modules").unlink()


if __name__ == "__main__":
    (ROOT / ".local").mkdir(exist_ok=True)
    unittest.main()
