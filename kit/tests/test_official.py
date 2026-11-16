import http.server
import json
import os
import shutil
import sys
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from test_automation import workspace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import official
from cases import ROOT, read_json, write_json


class NativeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "runs" / ("native-test-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "source-workspace").mkdir()
        _, self.source, self.draft = workspace(self.root / "source-workspace")
        self.url = "http://127.0.0.1:8123/"
        env = {k: v for k, v in os.environ.items() if not k.startswith(("APP_", "CRM_"))}
        env["APP_BASE_URL"] = self.url
        self.env = patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def prepared(self):
        return official.prepare(self.source, self.root / ("run-" + uuid.uuid4().hex), True, self.url)

    def author(self, run, entries=None):
        (run / "tests").mkdir(exist_ok=True)
        case = self.draft["cases"][0]
        title = f"{case['id']} | {case['title']}"
        spec = "tests/item.spec.ts"
        (run / "tests" / "item.spec.ts").write_text(
            "import { test, expect } from '../fixtures';\n"
            f"test({json.dumps(title)}, async ({{ page }}) => {{ "
            "await expect(page.locator('body')).toContainText('Controlled item'); });\n",
            encoding="utf-8")
        path = run / "input-manifest.json"
        write_json(path, {"schemaVersion": 2, "cases": entries if entries is not None
                          else [{"caseId": case["id"], "spec": spec, "title": title}]})
        return path

    def registered(self):
        run = self.prepared()
        return official.register(run, self.author(run), True, self.url)

    def test_prepare_review_and_expected_result(self):
        with self.assertRaisesRegex(ValueError, "confirm-approved-cases"):
            official.prepare(self.source, self.root / "missing", False, self.url)
        run = self.prepared()
        self.assertIn(self.draft["cases"][0]["expectedResult"], (run / "scenario.md").read_text())
        self.assertIn("playwright-cli -s=tw-XXXX resume", (run / "agent-task.txt").read_text())
        manifest = self.author(run)
        with self.assertRaisesRegex(ValueError, "confirm-approved-tests"):
            official.register(run, manifest, False, self.url)
        self.assertFalse((run / "playwright-mapping.json").exists())

    def test_missing_duplicate_extra_id_and_wrong_title_rejected(self):
        case = {"caseId": "TC-001", "spec": "tests/item.spec.ts", "title": "TC-001 | Find a controlled item"}
        for entries in [[], [case, case], [{**case, "caseId": "TC-999"}], [{**case, "title": "TC-001 | wrong"}]]:
            run = self.prepared()
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                official.register(run, self.author(run, entries), True, self.url)

    def test_tampering_source_and_native_and_target(self):
        mapping = self.registered()
        with patch.dict(os.environ, {"APP_BASE_URL": "http://127.0.0.1:9999"}, clear=True):
            with self.assertRaisesRegex(ValueError, "target differs"):
                official.execute(self.source, mapping)
        spec = mapping.parent / "tests" / "item.spec.ts"
        spec.write_text(spec.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            official.verify_mapping(mapping)
        mapping2 = self.registered()
        source = self.source / "draft.json"
        source.write_text(source.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "Source cases changed"):
            official.verify_mapping(mapping2)

    def test_folder_file_mapping_and_selected_ids(self):
        mapping = self.registered()
        for source in [self.source, self.source / "draft.json", self.source / "test-cases.xlsx", mapping.parent]:
            self.assertEqual(official.resolve_mapping(source, mapping), mapping)
        self.assertEqual(official.verify_mapping(mapping)["engine"], "playwright-cli")
        with self.assertRaisesRegex(ValueError, "not mapped"):
            official.execute(self.source, mapping, ["TC-999"])

    def test_reject_unsafe_native_patterns_and_paths(self):
        run = self.prepared()
        manifest = self.author(run)
        spec = run / "tests" / "item.spec.ts"
        spec.write_text(spec.read_text() + "\ntest.skip('not run', () => {});")
        with self.assertRaisesRegex(ValueError, "disallowed"):
            official.register(run, manifest, True, self.url)
        with self.assertRaisesRegex(ValueError, "[Pp]ath"):
            official.safe_file(run, "../outside")

    def test_native_file_rejects_unmapped_extra_test(self):
        run = self.prepared()
        manifest = self.author(run)
        spec = run / "tests" / "item.spec.ts"
        spec.write_text(spec.read_text() + "\ntest('extra', async () => {});\n")
        with self.assertRaisesRegex(ValueError, "exactly one test"):
            official.register(run, manifest, True, self.url)

    def test_login_is_prepared_and_pinned(self):
        login = {"username": "#username", "password": "#password", "submit": "#submit", "authenticated": "#ready"}
        path = self.root / "reviewed-login.json"
        write_json(path, login)
        run = official.prepare(self.source, self.root / "with-login", True, self.url, path)
        self.assertEqual(read_json(run / "login.json"), login)
        write_json(run / "login.json", None)
        with self.assertRaisesRegex(ValueError, "changed"):
            official.register(run, self.author(run), True, self.url)

    def test_manifest_can_be_named_manifest_json(self):
        run = self.prepared()
        manifest = self.author(run)
        manifest.rename(run / "manifest.json")
        mapping = official.register(run, run / "manifest.json", True, self.url)
        official.verify_mapping(mapping)

    def test_reporting_rejects_false_passes(self):
        case = {"caseId": "TC-001", "title": "TC-001 | Find", "spec": "tests/item.spec.ts"}
        def report(results, title=case["title"], file=case["spec"]):
            return {"suites": [{"specs": [{"title": title, "file": file, "tests": [{"results": results}]}]}]}
        self.assertEqual(official.report_cases(report([{"status": "passed"}]), [case])[0]["status"], "passed")
        for results in [[], [{"status": "skipped"}], [{"status": "failed"}, {"status": "passed"}]]:
            self.assertNotEqual(official.report_cases(report(results), [case])[0]["status"], "passed")
        for bad in [report([{"status": "passed"}], "other"), report([{"status": "passed"}], file="tests/other.spec.ts"), {"suites": []}]:
            with self.assertRaises(ValueError):
                official.report_cases(bad, [case])

    def test_native_browser_against_controlled_local_server(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            body = b"<html><body>Controlled item</body></html>"

            def do_GET(self):
                body = self.body
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_port}/"
        os.environ["APP_BASE_URL"] = self.url
        mapping = self.registered()
        for source in [self.source / "test-cases.xlsx", self.source / "draft.json",
                       self.source, mapping.parent]:
            with self.subTest(source=source):
                self.assertEqual(official.automation.execute(source, mapping, ["TC-001"]), 0)
        summary = next((mapping.parent / "executions").glob("*/execution-summary.json"))
        self.assertEqual(read_json(summary)["status"], "passed")
        Handler.body = b"<html><body>Unexpected result</body></html>"
        self.assertEqual(official.automation.execute(self.source, mapping, ["TC-001"]), 1)
        summaries = sorted((mapping.parent / "executions").glob("*/execution-summary.json"))
        self.assertEqual(read_json(summaries[-1])["cases"][0]["status"], "failed")

    def test_login_then_evidence_and_password_type_guard(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            writes = 0

            def do_GET(self):
                body = (b"<html><body id='ready'>Controlled item</body></html>" if self.path == "/ready" else
                        b"<html><body><form method='post'><input id='u'><input id='p' type='password'>"
                        b"<button id='submit' onclick=\"event.preventDefault();"
                        b"fetch('/business',{method:'POST'}).catch(()=>{}).finally(()=>"
                        b"HTMLFormElement.prototype.submit.call(this.form))\">"
                        b"Sign in</button></form></body></html>")
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def do_POST(self):
                if self.path == "/business":
                    Handler.writes += 1
                self.send_response(303)
                self.send_header("Location", "/ready")
                self.end_headers()
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_port}/"
        os.environ.update(APP_BASE_URL=self.url, APP_USERNAME="synthetic-user", APP_PASSWORD="synthetic-password")
        login = {"username": "#u", "password": "#p", "submit": "#submit", "authenticated": "#ready",
                 "requests": [{"method": "POST", "path": "/"}]}
        login_path = self.root / "login.json"
        write_json(login_path, login)
        run = official.prepare(self.source, self.root / "login-run", True, self.url, login_path)
        mapping = official.register(run, self.author(run), True, self.url)
        self.assertEqual(official.execute(self.source, mapping, evidence=True), 0)
        self.assertEqual(Handler.writes, 0)
        self.assertEqual(len(list((run / "executions").rglob("trace.zip"))), 1)
        self.assertEqual(len(list((run / "executions").rglob("outcome.png"))), 1)
        self.assertEqual(len(list((run / "executions").glob("*/html/index.html"))), 1)
        login["password"] = "#u"
        write_json(login_path, login)
        bad = official.prepare(self.source, self.root / "bad-login", True, self.url, login_path)
        mapping = official.register(bad, self.author(bad), True, self.url)
        self.assertEqual(official.execute(self.source, mapping, evidence=True), 1)
        self.assertFalse(list((bad / "executions").rglob("trace.zip")))
        self.assertFalse(list((bad / "executions").rglob("failure.png")))
        self.assertFalse(list((bad / "executions").rglob("outcome.png")))


if __name__ == "__main__":
    unittest.main()
