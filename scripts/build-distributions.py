"""Build the kit and plugin from explicit source allowlists."""

import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "kit"
PLUGIN = ROOT / "plugins" / "crm-testcase"
DIST = ROOT / "dist"
KIT_FILES = [
    ".gitignore", "README.md", "package.json", "package-lock.json", "requirements.txt",
    ".github/agents/crm-feature-explorer.agent.md",
    ".github/agents/crm-testcase-generator.agent.md",
    ".github/skills/crm-feature-exploration/SKILL.md",
    ".github/skills/crm-playwright-automation/SKILL.md",
    ".github/skills/crm-testcase-generation/SKILL.md",
    "prompts/automate.txt", "prompts/explore.txt", "prompts/generate.txt",
    "scripts/automation.py", "scripts/capture.cjs", "scripts/cases.py", "scripts/explore.cjs",
    "templates/playwright-runtime.cjs", "templates/playwright.config.cjs",
    "tests/automation-browser.py", "tests/capture.test.cjs", "tests/explore.test.cjs",
    "tests/fixtures.py", "tests/prompt-browser.test.cjs", "tests/test_automation.py", "tests/test_cases.py",
]
PLUGIN_FILES = [
    "plugin.json", "README.md", "skills/crm-testcase/SKILL.md",
    "skills/crm-testcase/scripts/initialize.cjs",
    "com.github.copilot/agents/crm-testcase.agent.md",
    "com.github.copilot/commands/explore.md",
    "com.github.copilot/commands/generate-cases.md",
    "com.github.copilot/commands/create-tests.md",
    "com.github.copilot/commands/run-tests.md",
    "tests/initialize.test.cjs", "tests/commands.test.cjs",
]


def digest(content):
    return hashlib.sha256(content).hexdigest()


def source_files(root, names):
    result = {}
    for name in names:
        path = root.joinpath(*name.split("/"))
        if not path.is_file() or any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent):
            raise ValueError(f"Missing source or symlink refused: {path}")
        result[name] = path.read_bytes()
    return result


def manifest(payload, **metadata):
    return (json.dumps({
        "schemaVersion": 1, **metadata,
        "files": {name: digest(content) for name, content in sorted(payload.items())},
        "note": "Hash integrity manifest, not a signature.",
    }, indent=2) + "\n").encode("utf-8")


def archive(path, payload):
    with ZipFile(path, "w", ZIP_DEFLATED) as output:
        for name, content in sorted(payload.items()):
            output.writestr(name, content)
    with ZipFile(path) as output:
        if set(output.namelist()) != set(payload) or any(output.read(name) != data for name, data in payload.items()):
            raise ValueError(f"Archive verification failed: {path.name}")


def frontmatter_context(original, context):
    text = original.decode("utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise ValueError("Missing YAML front matter")
    end = text.index("\n---", 4) + len("\n---")
    return (text[:end] + "\n\n" + context + "\n" + text[end:]).encode("utf-8")


def build():
    kit = source_files(KIT, KIT_FILES)
    plugin = source_files(PLUGIN, PLUGIN_FILES)
    kit_version = json.loads(kit["package.json"])["version"]
    plugin_info = json.loads(plugin["plugin.json"])
    kit["MANIFEST.json"] = manifest(kit, package="CRM-Testcase-Customer-Kit", version=kit_version)
    for name, content in kit.items():
        plugin[f"skills/crm-testcase/kit/{name}"] = content
    for name in ("crm-feature-exploration", "crm-testcase-generation", "crm-playwright-automation"):
        plugin[f"skills/{name}/SKILL.md"] = frontmatter_context(
            kit[f".github/skills/{name}/SKILL.md"],
            "## Installed plugin context\n\nFirst use the crm-testcase skill to initialize a fresh workspace. "
            "File references below refer to that workspace, not the plugin installation. "
            "Never write customer data or install dependencies in the plugin directory.",
        )
    for name in ("crm-feature-explorer", "crm-testcase-generator"):
        plugin[f"com.github.copilot/agents/{name}.agent.md"] = frontmatter_context(
            kit[f".github/agents/{name}.agent.md"],
            "Plugin context: first use the crm-testcase skill to initialize a workspace. "
            "File references below are relative to that workspace. Do not modify the plugin "
            "installation or recursively start its main agent.",
        )
    plugin["BUNDLE-MANIFEST.json"] = manifest(
        plugin, plugin=plugin_info["name"], version=plugin_info["version"], customerKitVersion=kit_version,
    )
    DIST.mkdir(exist_ok=True)
    extracted = DIST / "crm-testcase-plugin"
    if extracted.is_symlink():
        raise ValueError("Refusing to replace symlinked distribution directory")
    if extracted.exists():
        shutil.rmtree(extracted)
    for name, content in plugin.items():
        path = extracted.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    archive(DIST / f"CRM-Testcase-Customer-Kit-{kit_version}.zip", kit)
    archive(DIST / f"CRM-Testcase-Copilot-Plugin-{plugin_info['version']}.zip", plugin)
    print(f"Built and verified kit ({len(kit)} files) and plugin ({len(plugin)} files) in dist/")


if __name__ == "__main__":
    build()
