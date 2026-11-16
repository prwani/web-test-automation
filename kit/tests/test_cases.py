import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook
from fixtures import write_brd, write_observations

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cases import ROOT, STATUS, brd_units, export_run, export_workbook, make_request, observations, sha, validate_draft, write_json


class CaseGenerationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.ui = write_observations(directory.name)
        self.request = make_request("ui-only", self.ui)
        self.draft = {
            "schemaVersion": 1, "mode": "ui-only", "scope": self.request["scope"],
            "cases": [{
                "id": "TC-001", "title": "Find an item", "category": "positive", "priority": "High",
                "preconditions": ["An authorized user and controlled items"],
                "steps": ["Open search", "Search for ITEM_A"], "expectedResult": "ITEM_A is shown",
                "expectedBasis": "observed", "requirementRefs": [], "observationRefs": ["UI-002"], "assumptions": [],
            }], "questions": [],
        }

    def test_ui_only_contains_no_brd(self):
        self.assertEqual(self.request["sourceUnits"], [])
        self.assertEqual([s["kind"] for s in self.request["sources"]], ["reviewed-ui"])
        validate_draft(self.request, self.draft)

    def test_feature_navigation_scope_reaches_generation_without_becoming_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            data = json.loads(self.ui.read_text(encoding="utf-8"))
            data["scope"] = "Explore item search and clearing search. Navigation: main menu > Search."
            path = Path(directory) / "reviewed.json"
            write_json(path, data)
            request = make_request("ui-only", path)
            self.assertEqual(request["scope"], data["scope"])
            self.assertEqual(request["responseSchema"]["scope"], data["scope"])
            self.assertEqual(request["sourceUnits"], [])
            self.assertEqual(request["observations"], data["observations"])

    def test_mode_requires_or_forbids_brd(self):
        with self.assertRaisesRegex(ValueError, "requires"):
            make_request("ui-brd", self.ui)
        with self.assertRaisesRegex(ValueError, "forbids"):
            make_request("ui-only", self.ui, Path("should-not-be-read.docx"))

    def test_ui_brd_preserves_generic_source_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_brd(directory)
            request = make_request("ui-brd", self.ui, path)
            self.assertTrue(any("REQ-42" in u["text"] for u in request["sourceUnits"]))
            self.assertTrue(all(u["id"].startswith("BRD-") for u in request["sourceUnits"]))

    def test_unreviewed_capture_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.json"
            data = json.loads(self.ui.read_text())
            data["reviewed"] = False
            write_json(path, data)
            with self.assertRaisesRegex(ValueError, "reviewed"):
                observations(path)

    def test_unknown_observation_rejected(self):
        self.draft["cases"][0]["observationRefs"] = ["UI-999"]
        with self.assertRaisesRegex(ValueError, "unknown"):
            validate_draft(self.request, self.draft)

    def test_invented_ui_only_requirements_rejected(self):
        self.draft["cases"][0]["expectedBasis"] = "requirement"
        with self.assertRaisesRegex(ValueError, "cite"):
            validate_draft(self.request, self.draft)

    def test_proposed_expectations_need_assumptions(self):
        self.draft["cases"][0]["expectedBasis"] = "proposed"
        with self.assertRaisesRegex(ValueError, "assumptions"):
            validate_draft(self.request, self.draft)
        self.draft["cases"][0]["assumptions"] = ["Business owner must confirm matching rules"]
        validate_draft(self.request, self.draft)

    def test_duplicate_ids_rejected(self):
        self.draft["cases"].append(copy.deepcopy(self.draft["cases"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_draft(self.request, self.draft)

    def test_empty_steps_rejected(self):
        self.draft["cases"][0]["steps"] = []
        with self.assertRaisesRegex(ValueError, "nonempty"):
            validate_draft(self.request, self.draft)

    def test_model_cannot_claim_pass_status(self):
        self.draft["cases"][0]["status"] = "Passed"
        with self.assertRaisesRegex(ValueError, "exactly"):
            validate_draft(self.request, self.draft)

    def test_invalid_enum_type_rejected_explicitly(self):
        self.draft["cases"][0]["category"] = []
        with self.assertRaisesRegex(ValueError, "category"):
            validate_draft(self.request, self.draft)

    def test_excel_cannot_silently_truncate_long_steps(self):
        self.draft["cases"][0]["steps"] = ["A" * 20000, "B" * 20000]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.xlsx"
            with self.assertRaisesRegex(ValueError, "Excel"):
                export_workbook(self.request, self.draft, path)
            self.assertFalse(path.exists())

    def test_workbook_formulas_neutralized_and_status_draft(self):
        self.draft["cases"][0]["title"] = '=HYPERLINK("https://example.invalid","do not execute")'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.xlsx"
            export_workbook(self.request, self.draft, path)
            workbook = load_workbook(path)
            try:
                sheet = workbook["Test Cases"]
                self.assertEqual(sheet["B2"].data_type, "s")
                self.assertEqual(sheet["L2"].value, STATUS)
                self.assertEqual(sheet["M2"].value, "Not Executed")
                self.assertEqual(workbook["BRD Sources"].max_row, 1)
                self.assertTrue(any("Unmapped" in str(row[3].value) for row in workbook["Traceability"]))
                self.assertFalse(any(c.data_type == "f" for ws in workbook for row in ws for c in row))
            finally:
                workbook.close()

    def test_tampered_request_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            write_json(run / "request.json", self.request)
            write_json(run / "provenance.json", {"requestSha256": "wrong"})
            write_json(run / "draft.json", self.draft)
            with self.assertRaisesRegex(ValueError, "changed"):
                export_run(run)

    def test_generic_docx_paragraph_not_cs_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generic.docx"
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>REQ-42: Search items by name.</w:t></w:r></w:p></w:body></w:document>')
            self.assertEqual(brd_units(path)[0]["text"], "REQ-42: Search items by name.")

    def test_tracked_changes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changes.docx"
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:ins><w:r><w:t>Ambiguous change</w:t></w:r></w:ins></w:p></w:body></w:document>')
            with self.assertRaisesRegex(ValueError, "tracked"):
                brd_units(path)


if __name__ == "__main__":
    unittest.main()
