import json
from pathlib import Path
from zipfile import ZipFile


def write_observations(directory):
    path = Path(directory) / "observations.json"
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "scope": "Search a controlled list",
        "reviewed": True,
        "observations": [
            {
                "id": "UI-001", "title": "Open the list",
                "actions": ["Open the list"],
                "outcome": "The list is visible",
                "evidence": "Synthetic test fixture",
            },
            {
                "id": "UI-002", "title": "Search",
                "actions": ["Search for the first item"],
                "outcome": "The first item is visible and the second is absent",
                "evidence": "Synthetic test fixture",
            },
        ],
    }), encoding="utf-8")
    return path


def write_brd(directory):
    path = Path(directory) / "requirements.docx"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>REQ-42: Search by name.</w:t></w:r></w:p></w:body></w:document>',
        )
    return path
