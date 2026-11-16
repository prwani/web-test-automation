import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook
from fixtures import write_observations

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import automation
from cases import ROOT, export_workbook, make_request, read_json, write_json


def workspace(directory):
    root = Path(directory)
    (root / "templates").mkdir()
    (root / "prompts").mkdir()
    for name in ["playwright-runtime.cjs", "playwright.config.cjs"]:
        shutil.copyfile(ROOT / "templates" / name, root / "templates" / name)
    shutil.copyfile(ROOT / "prompts" / "automate.txt", root / "prompts" / "automate.txt")
    source = root / "runs" / "source"
    source.mkdir(parents=True)
    request = make_request("ui-only", write_observations(root))
    draft = {
        "schemaVersion": 1, "mode": "ui-only", "scope": request["scope"], "questions": [],
        "cases": [{
            "id": "TC-001", "title": "Find a controlled item", "category": "positive", "priority": "High",
            "preconditions": ["Controlled test environment and two fixture items"],
            "steps": ["Search for the first item"],
            "expectedResult": "First item is visible; second is excluded",
            "expectedBasis": "observed", "requirementRefs": [], "observationRefs": ["UI-002"], "assumptions": [],
        }],
    }
    write_json(source / "request.json", request)
    write_json(source / "draft.json", draft)
    export_workbook(request, draft, source / "test-cases.xlsx")
    return root, source, draft


def minimal_plan():
    return {"schemaVersion": 1, "login": None, "cases": [{
        "caseId": "TC-001", "steps": [{"action": "expectVisible", "target": {"by": "css", "value": "#result"}}],
    }]}


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root, self.source, self.draft = workspace(self.directory.name)
        self.root_patch = patch.object(automation, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def compile(self, name="automation"):
        run = automation.prepare(self.source, self.root / "runs" / name, True)
        write_json(run / "plan.json", minimal_plan())
        return automation.compile_plan(run, run / "plan.json", True, "http://127.0.0.1:8123")

    def test_workbook_json_folder_resolve_same_cases(self):
        for source in [self.source, self.source / "test-cases.xlsx", self.source / "draft.json"]:
            draft, sources = automation.source_cases(source)
            self.assertEqual(draft, self.draft)
            self.assertEqual({s["kind"] for s in sources}, {"workbook", "draft", "generation-request"})

    def test_standalone_workbook_requires_companion_inputs(self):
        (self.source / "draft.json").unlink()
        with self.assertRaisesRegex(ValueError, "companion"):
            automation.source_cases(self.source / "test-cases.xlsx")

    def test_edited_workbook_does_not_silently_run_stale_json(self):
        path = self.source / "test-cases.xlsx"
        workbook = load_workbook(path)
        workbook["Test Cases"]["G2"] = "Changed acceptance criteria"
        workbook.save(path)
        workbook.close()
        with self.assertRaisesRegex(ValueError, "differ"):
            automation.source_cases(path)

    def test_case_approval_required_before_preparation(self):
        with self.assertRaisesRegex(ValueError, "confirm-approved-cases"):
            automation.prepare(self.source, self.root / "runs" / "not-created")
        self.assertFalse((self.root / "runs" / "not-created").exists())

    def test_plan_rejects_missing_duplicate_extra_case_ids(self):
        for ids in [[], ["TC-001", "TC-001"], ["TC-999"]]:
            plan = minimal_plan()
            plan["cases"] = [{**copy.deepcopy(plan["cases"][0]), "caseId": identifier} for identifier in ids]
            with self.assertRaisesRegex(ValueError, "exactly once"):
                automation.validate_plan(plan, self.draft["cases"])

    def test_plan_rejects_omitted_assertions_arbitrary_code_and_external_navigation(self):
        bad_steps = [
            [{"action": "click", "target": {"by": "css", "value": "#search"}}],
            [{"action": "evaluate", "code": "page.evaluate('anything')"}],
            [{"action": "goto", "path": "//external.invalid"}],
            [{"action": "goto", "path": "/\\external.invalid"}],
            [{"action": "expectCount", "target": {"by": "css", "value": "#results"}, "value": True}],
            [{"action": "expectVisible", "target": {"by": "css", "value": "#results"}, "skip": True}],
        ]
        for steps in bad_steps:
            plan = minimal_plan()
            plan["cases"][0]["steps"] = steps
            with self.assertRaises(ValueError):
                automation.validate_plan(plan, self.draft["cases"])

    def test_compile_requires_plan_review_and_never_overwrites(self):
        run = automation.prepare(self.source, self.root / "runs" / "automation", True)
        write_json(run / "plan.json", minimal_plan())
        with self.assertRaisesRegex(ValueError, "confirm-approved-plan"):
            automation.compile_plan(run, run / "plan.json")
        automation.compile_plan(run, run / "plan.json", True, "http://127.0.0.1:8123")
        with self.assertRaisesRegex(ValueError, "already exists"):
            automation.compile_plan(run, run / "plan.json", True, "http://127.0.0.1:8123")

    def test_changed_preparation_or_source_rejected_before_compilation(self):
        run = automation.prepare(self.source, self.root / "runs" / "automation", True)
        write_json(run / "plan.json", minimal_plan())
        path = self.source / "draft.json"
        path.write_text(path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "Source cases changed"):
            automation.compile_plan(run, run / "plan.json", True)
        request = run / "automation-request.json"
        request.write_text(request.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "request changed"):
            automation.compile_plan(run, run / "plan.json", True)
        self.assertFalse((run / "tests").exists())

    def test_mapping_resolves_all_supported_references_including_identical_copied_workbook(self):
        mapping = self.compile()
        for source in [self.source, self.source / "test-cases.xlsx", self.source / "draft.json", mapping.parent]:
            self.assertEqual(automation.resolve_mapping(source), mapping)
        copied = self.root / "copied.xlsx"
        shutil.copyfile(self.source / "test-cases.xlsx", copied)
        self.assertEqual(automation.resolve_mapping(copied), mapping)
        self.assertEqual(automation.verify_mapping(mapping)["cases"][0]["caseId"], "TC-001")

    def test_missing_stale_ambiguous_mappings_fail_instead_of_guessing(self):
        with self.assertRaisesRegex(ValueError, "No matching mapping"):
            automation.resolve_mapping(self.source)
        first = self.compile()
        second = self.compile("automation-two")
        with self.assertRaisesRegex(ValueError, "Multiple mappings"):
            automation.resolve_mapping(self.source)
        self.assertEqual(automation.resolve_mapping(self.source, second), second)
        path = self.source / "draft.json"
        path.write_text(path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "No matching mapping"):
            automation.resolve_mapping(path, first)

    def test_modified_compiled_behavior_and_case_mapping_are_rejected(self):
        mapping = self.compile()
        plan = mapping.parent / "compiled-plan.json"
        plan.write_text(plan.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "changed"):
            automation.verify_mapping(mapping)
        other = self.compile("other")
        content = read_json(other)
        content["cases"][0]["requirementRefs"] = ["INVENTED"]
        write_json(other, content)
        with self.assertRaisesRegex(ValueError, "does not match"):
            automation.verify_mapping(other)

    def test_reporting_preserves_failures_skips_and_missing_or_retried_cases(self):
        case = {"caseId": "TC-001", "title": "TC-001 | Find"}
        for results, expected in [
            ([{"status": "passed", "duration": 12}], "passed"),
            ([{"status": "failed"}], "failed"), ([{"status": "skipped"}], "skipped"),
            ([], "missing-or-retried"),
            ([{"status": "failed"}, {"status": "passed"}], "missing-or-retried"),
        ]:
            report = {"suites": [{"specs": [{"title": case["title"], "tests": [{"results": results}]}]}]}
            actual = automation.report_cases(report, [case])
            self.assertEqual(actual[0]["caseId"], "TC-001")
            self.assertEqual(actual[0]["status"], expected)

    def test_execution_rejects_wrong_crm_before_launching_browser(self):
        self.compile()
        with patch.dict(automation.os.environ, {"CRM_BASE_URL": "http://127.0.0.1:9999"}):
            with self.assertRaisesRegex(ValueError, "target differs"):
                automation.execute(self.source)
        self.assertFalse(any((self.root / "runs" / "automation").glob("executions/*")))

    def test_application_aliases_and_conflicts(self):
        for suffix, first, second in [
            ("BASE_URL", "https://example.invalid/a", "https://example.invalid/b"),
            ("APPROVED_BASE_URL", "https://example.invalid/a", "https://example.invalid/b"),
            ("USERNAME", "first", "second"),
            ("PASSWORD", "first", "second"),
            ("DATA_ITEM", "first", "second"),
            ("CASE_IDS", '["TC-001"]', '["TC-002"]'),
        ]:
            with self.subTest(suffix=suffix):
                env = {f"APP_{suffix}": first, f"CRM_{suffix}": second}
                with self.assertRaisesRegex(ValueError, "Conflicting"):
                    automation.check_aliases(env)
                self.assertEqual(automation.aliased({f"APP_{suffix}": first}, suffix), first)
                self.assertEqual(automation.aliased({f"CRM_{suffix}": first}, suffix), first)
        automation.check_aliases({"APP_BASE_URL": "https://example.invalid", "CRM_BASE_URL": "https://example.invalid/"})

    def test_compile_and_execute_reject_conflicting_targets(self):
        run = automation.prepare(self.source, self.root / "runs" / "conflicts", True)
        write_json(run / "plan.json", minimal_plan())
        with patch.dict(automation.os.environ, {"APP_BASE_URL": "http://127.0.0.1:8123",
                                                "CRM_BASE_URL": "http://127.0.0.1:9999"}, clear=True):
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                automation.compile_plan(run, run / "plan.json", True)
        with patch.dict(automation.os.environ, {"APP_BASE_URL": "http://127.0.0.1:8123"}, clear=True):
            with self.assertRaisesRegex(ValueError, "conflicts"):
                automation.compile_plan(run, run / "plan.json", True, "http://127.0.0.1:9999")
            automation.compile_plan(run, run / "plan.json", True)
        with patch.dict(automation.os.environ, {"APP_BASE_URL": "http://127.0.0.1:9999"}, clear=True):
            with self.assertRaisesRegex(ValueError, "target differs"):
                automation.execute(self.source)
        with patch.dict(automation.os.environ, {"APP_BASE_URL": "http://127.0.0.1:8123",
                                                "APP_DATA_ITEM": "a", "CRM_DATA_ITEM": "b"}, clear=True):
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                automation.execute(self.source)
        self.assertFalse((run / "executions").exists())

    def test_mapping_rejects_insecure_or_secret_bearing_crm_urls(self):
        for value in [None, "http://external.invalid", "https://user:password@crm.invalid",
                      "https://crm.invalid?token=forbidden", "https://crm.invalid#secret",
                      "https://crm.invalid\\other", " https://crm.invalid"]:
            with self.assertRaises(ValueError):
                automation.crm_url(value)


if __name__ == "__main__":
    unittest.main()
