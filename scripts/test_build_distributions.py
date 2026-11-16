import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).absolute().parent
spec = importlib.util.spec_from_file_location("builder", HERE / "build-distributions.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuilderSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_refuses_unsafe_duplicate_and_conflicting_names(self):
        for names in (["../outside"], ["a\\b"], ["C:/a"], ["a//b"], ["NUL.txt"],
                      ["x", "X"], ["a", "a/b"]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                builder.validate_names(names)

    def test_archive_has_exact_verified_payload(self):
        path = self.root / "output.zip"
        payload = {"one": b"one", "nested/two": b"two"}
        builder.archive(path, payload)
        with ZipFile(path) as archive:
            self.assertEqual(set(archive.namelist()), set(payload))
            self.assertEqual({name: archive.read(name) for name in payload}, payload)
        builder.archive(path, payload)

    def test_removal_requires_unmodified_exact_owned_bundle(self):
        directory = self.root / "bundle"
        directory.mkdir()
        (directory / "file").write_bytes(b"contents")
        (directory / "BUNDLE-MANIFEST.json").write_bytes(
            builder.manifest({"file": b"contents"}, plugin="web-test", version="1.0.0"))
        extra = directory / "extra"
        extra.write_text("preserve")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            builder.remove_owned_distribution(directory)
        self.assertTrue(extra.exists())
        extra.unlink()
        (directory / "file").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "modified"):
            builder.remove_owned_distribution(directory)
        (directory / "file").write_bytes(b"contents")
        builder.remove_owned_distribution(directory)
        self.assertFalse(directory.exists())

    def test_rejects_redirected_distribution_target(self):
        target = self.root / "target"
        target.mkdir()
        sentinel = target / "preserve"
        sentinel.write_text("preserve")
        link = self.root / "redirected"
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           check=True, capture_output=True)
        else:
            link.symlink_to(target, target_is_directory=True)
        try:
            with self.assertRaisesRegex(ValueError, "Symlink or junction"):
                builder.remove_owned_distribution(link)
            self.assertEqual(sentinel.read_text(), "preserve")
        finally:
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()

    def test_build_rebuild_and_neutral_manifest_contract(self):
        kit = self.root / "kit"
        kit.mkdir()
        names = [
            "package.json", "README.md",
            ".github/skills/web-feature-exploration/SKILL.md",
            ".github/skills/web-testcase-generation/SKILL.md",
            ".github/skills/web-playwright-automation/SKILL.md",
            ".github/agents/web-feature-explorer.agent.md",
            ".github/agents/web-testcase-generator.agent.md",
        ]
        for name in names:
            path = kit.joinpath(*name.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                '{"version":"1.3.0"}' if name == "package.json" else
                "---\nname: fixture\n---\nBody\n" if name.endswith(".md") and name != "README.md" else
                "Synthetic kit\n", encoding="utf-8")
        dist = self.root / "dist"
        with patch.object(builder, "KIT", kit), patch.object(builder, "DIST", dist), \
                patch.object(builder, "KIT_FILES", names):
            builder.build()
            builder.build()
        with ZipFile(dist / "Web-Test-Automation-Kit-1.3.0.zip") as archive:
            kit_manifest = json.loads(archive.read("MANIFEST.json"))
            self.assertEqual(kit_manifest["package"], "Web-Test-Automation-Kit")
            self.assertEqual(set(kit_manifest["files"]), set(names))
        plugin_version = json.loads((builder.PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
        with ZipFile(dist / f"Web-Test-Copilot-Plugin-{plugin_version}.zip") as archive:
            kit_manifest = json.loads(archive.read("skills/web-test/kit/MANIFEST.json"))
            self.assertEqual(kit_manifest["package"], "Web-Test-Automation-Kit")
            self.assertIn("skills/web-feature-exploration/SKILL.md", archive.namelist())
            self.assertIn("com.github.copilot/agents/web-feature-explorer.agent.md", archive.namelist())
        self.assertTrue((dist / "web-test-plugin" / "BUNDLE-MANIFEST.json").is_file())


if __name__ == "__main__":
    unittest.main()
