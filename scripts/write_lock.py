"""Record the exact distributions installed in the verified Python environment."""

from importlib.metadata import distributions
from pathlib import Path

root = Path(__file__).resolve().parents[1]
versions = {}
for distribution in distributions():
    name = distribution.metadata["Name"]
    if name.lower() != "commercegraph":
        versions[name.lower().replace("_", "-")] = distribution.version
content = "# Exact versions from the Python 3.12 validation environment.\n"
content += "# Install the local package separately with --no-deps.\n"
content += "\n".join(f"{name}=={version}" for name, version in sorted(versions.items())) + "\n"
(root / "requirements.lock.txt").write_text(content, encoding="utf-8")
print(f"Locked {len(versions)} distributions; no machine-specific editable paths.")
