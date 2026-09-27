import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {".venv", ".git", "__pycache__", ".pytest_cache", "private", "prepared"}
BANNED = [
    "/Users/",
    "/home/",
    "op://",
    "life_record",
    "Mercer",
    "sounds_sample",
    "agreement2",
    "voicekey_CAE",
    "grapeot@",
]


def test_public_tree_has_no_private_markers():
    hits = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP for part in path.parts):
            continue
        if path.name == "test_hygiene.py":
            continue
        if not path.is_file():
            continue
        if path.suffix in {".wav", ".m4a", ".mp3", ".pyc"}:
            hits.append(str(path.relative_to(ROOT)))
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in BANNED:
            if token in text:
                hits.append(f"{path.relative_to(ROOT)}:{token}")
    assert hits == []
