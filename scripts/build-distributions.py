"""Build the kit and plugin from explicit source allowlists."""

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).absolute().parent.parent
KIT = ROOT / "kit"
PLUGIN = ROOT / "plugins" / "web-test"
DIST = ROOT / "dist"
KIT_FILES = [
    ".gitignore", "README.md", "package.json", "package-lock.json", "requirements.txt",
    ".github/agents/web-feature-explorer.agent.md",
    ".github/agents/web-testcase-generator.agent.md",
    ".github/skills/web-feature-exploration/SKILL.md",
    ".github/skills/web-playwright-automation/SKILL.md",
    ".github/skills/web-testcase-generation/SKILL.md",
    "prompts/automate.txt", "prompts/explore.txt", "prompts/generate.txt",
    "scripts/automation.py", "scripts/capture.cjs", "scripts/cases.py", "scripts/explore.cjs",
    "scripts/official.py", "scripts/playwright-skill.cjs",
    "templates/playwright-runtime.cjs", "templates/playwright.config.cjs",
    "templates/official-fixtures.ts", "templates/official-seed.spec.ts", "templates/official-playwright.config.cjs",
    "tests/automation-browser.py", "tests/capture.test.cjs", "tests/explore.test.cjs",
    "tests/fixtures.py", "tests/prompt-browser.test.cjs", "tests/test_automation.py", "tests/test_cases.py",
    "tests/test_official.py", "tests/playwright-skill.test.cjs",
]
PLUGIN_FILES = [
    "plugin.json", "README.md", "skills/web-test/SKILL.md",
    "skills/web-test/scripts/initialize.cjs",
    "com.github.copilot/agents/web-test.agent.md",
    "com.github.copilot/commands/explore.md",
    "com.github.copilot/commands/generate-cases.md",
    "com.github.copilot/commands/create-tests.md",
    "com.github.copilot/commands/run-tests.md",
    "tests/initialize.test.cjs", "tests/commands.test.cjs",
]


def digest(content):
    return hashlib.sha256(content).hexdigest()


def safe_name(name):
    parts = name.split("/")
    if (not name or name.startswith("/") or "\\" in name or ":" in name or
            any(not p or p in (".", "..") or p[-1] in ". " or
                re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?", p)
                for p in parts)):
        raise ValueError(f"Unsafe archive member: {name!r}")


def no_links(path):
    for entry in (path, *path.parents):
        reparse_point = (
            os.name == "nt" and entry.exists()
            and entry.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        if entry.is_symlink() or reparse_point:
            raise ValueError(f"Symlink or junction refused: {entry}")


def validate_names(names):
    seen = set()
    for name in names:
        safe_name(name)
        key = name.casefold()
        if any(key == old or key.startswith(old + "/") or old.startswith(key + "/") for old in seen):
            raise ValueError(f"Duplicate or conflicting archive member: {name}")
        seen.add(key)


def source_files(root, names):
    no_links(root)
    validate_names(names)
    result = {}
    for name in names:
        path = root.joinpath(*name.split("/"))
        no_links(path)
        if not path.is_file():
            raise ValueError(f"Missing source: {path}")
        result[name] = path.read_bytes()
    return result


def manifest(payload, **metadata):
    return (json.dumps({
        "schemaVersion": 1, **metadata,
        "files": {name: digest(content) for name, content in sorted(payload.items())},
        "note": "Hash integrity manifest, not a signature.",
    }, indent=2) + "\n").encode("utf-8")


def add(payload, name, content):
    validate_names([*payload, name])
    payload[name] = content


def archive(path, payload):
    validate_names(payload)
    no_links(path)
    if path.exists():
        if not path.is_file():
            raise ValueError(f"Archive target is not a regular file: {path}")
        path.unlink()
    with ZipFile(path, "x", ZIP_DEFLATED) as output:
        for name, content in sorted(payload.items()):
            output.writestr(name, content)
    with ZipFile(path) as output:
        names = output.namelist()
        validate_names(names)
        if (len(names) != len(payload) or set(names) != set(payload) or
                any(digest(output.read(name)) != digest(data) for name, data in payload.items())):
            raise ValueError(f"Archive verification failed: {path.name}")


def remove_owned_distribution(directory):
    """Only remove a previous intact generated bundle, never arbitrary files."""
    no_links(directory)
    if not directory.exists():
        return
    if not directory.is_dir():
        raise ValueError(f"Distribution target is not a directory: {directory}")
    marker = directory / "BUNDLE-MANIFEST.json"
    no_links(marker)
    if not marker.is_file():
        raise ValueError(f"Refusing to replace unrecognized distribution: {directory}")
    previous = json.loads(marker.read_text(encoding="utf-8"))
    if previous.get("schemaVersion") != 1 or previous.get("plugin") != "web-test":
        raise ValueError("Invalid previous distribution manifest")
    files = previous.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Invalid previous distribution file list")
    validate_names([*files, "BUNDLE-MANIFEST.json"])
    expected = set(files) | {"BUNDLE-MANIFEST.json"}
    actual = set()
    directories = []
    for path in directory.rglob("*"):
        no_links(path)
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
        elif path.is_dir():
            directories.append(path)
        else:
            raise ValueError(f"Unexpected distribution entry: {path}")
    if actual != expected:
        raise ValueError("Refusing to replace distribution with missing or unexpected files")
    expected_directories = set()
    for name in expected:
        parts = name.split("/")
        expected_directories.update("/".join(parts[:i]) for i in range(1, len(parts)))
    if {p.relative_to(directory).as_posix() for p in directories} != expected_directories:
        raise ValueError("Refusing to replace distribution with unexpected directories")
    for name, expected_hash in files.items():
        if digest(directory.joinpath(*name.split("/")).read_bytes()) != expected_hash:
            raise ValueError(f"Refusing to replace modified distribution file: {name}")
    for name in expected:
        directory.joinpath(*name.split("/")).unlink()
    for path in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        path.rmdir()
    directory.rmdir()


def frontmatter_context(original, context):
    text = original.decode("utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise ValueError("Missing YAML front matter")
    end = text.index("\n---", 4) + len("\n---")
    return (text[:end] + "\n\n" + context + "\n" + text[end:]).encode("utf-8")


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", value):
        raise ValueError("Invalid package version")
    return value


def build():
    no_links(ROOT)
    no_links(DIST)
    kit = source_files(KIT, KIT_FILES)
    plugin = source_files(PLUGIN, PLUGIN_FILES)
    kit_version = version(json.loads(kit["package.json"])["version"])
    plugin_info = json.loads(plugin["plugin.json"])
    if plugin_info["name"] != "web-test":
        raise ValueError("Invalid plugin identity")
    plugin_version = version(plugin_info["version"])
    add(kit, "MANIFEST.json", manifest(kit, package="Web-Test-Automation-Kit", version=kit_version))
    for name, content in kit.items():
        add(plugin, f"skills/web-test/kit/{name}", content)
    for name in ("web-feature-exploration", "web-testcase-generation", "web-playwright-automation"):
        add(plugin, f"skills/{name}/SKILL.md", frontmatter_context(
            kit[f".github/skills/{name}/SKILL.md"],
            "## Installed plugin context\n\nFirst use the web-test skill to initialize a fresh workspace. "
            "File references below refer to that workspace, not the plugin installation. "
            "Never write application data or install dependencies in the plugin directory.",
        ))
    for name in ("web-feature-explorer", "web-testcase-generator"):
        add(plugin, f"com.github.copilot/agents/{name}.agent.md", frontmatter_context(
            kit[f".github/agents/{name}.agent.md"],
            "Plugin context: first use the web-test skill to initialize a workspace. "
            "File references below are relative to that workspace. Do not modify the plugin "
            "installation or recursively start its main agent.",
        ))
    add(plugin, "BUNDLE-MANIFEST.json", manifest(
        plugin, plugin=plugin_info["name"], version=plugin_version, kitVersion=kit_version,
    ))
    DIST.mkdir(exist_ok=True)
    extracted = DIST / "web-test-plugin"
    remove_owned_distribution(extracted)
    extracted.mkdir()
    for name, content in plugin.items():
        path = extracted.joinpath(*name.split("/"))
        no_links(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    archive(DIST / f"Web-Test-Automation-Kit-{kit_version}.zip", kit)
    archive(DIST / f"Web-Test-Copilot-Plugin-{plugin_version}.zip", plugin)
    print(f"Built and verified kit ({len(kit)} files) and plugin ({len(plugin)} files) in dist/")


if __name__ == "__main__":
    build()
