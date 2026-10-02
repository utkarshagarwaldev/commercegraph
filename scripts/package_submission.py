"""Create a source review archive from an explicit allowlist, excluding local secrets."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from commercegraph.config import Settings

root = Path(__file__).resolve().parents[1]
directories = ["src", "tests", "scripts", "data", "examples", "docs", ".streamlit"]
filenames = [
    "app.py",
    "pyproject.toml",
    "requirements.lock.txt",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "README.md",
]
paths = [root / name for name in filenames]
for directory in directories:
    paths.extend(path for path in (root / directory).rglob("*") if path.is_file())
paths = sorted(
    path
    for path in paths
    if not any(part == "__pycache__" or part.endswith(".egg-info") for part in path.parts)
    and path.suffix != ".pyc"
    and path.name != "secrets.toml"
    and (not path.name.startswith(".env") or path.name == ".env.example")
)
secret = Settings.from_env().api_key.encode()
for path in paths:
    if secret and secret in path.read_bytes():
        raise SystemExit("Packaging blocked: a submission file contains the configured API key.")
destination = root / "dist" / "CommerceGraph-review.zip"
destination.parent.mkdir(exist_ok=True)
with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
    for path in paths:
        archive.write(path, str(path.relative_to(root)).replace("\\", "/"))
with ZipFile(destination) as archive:
    if archive.testzip() is not None:
        raise SystemExit("Archive integrity failed")
    assert ".env" not in archive.namelist()
print(f"Created {destination.name}: {len(paths)} files; local key excluded; ZIP integrity passed.")
