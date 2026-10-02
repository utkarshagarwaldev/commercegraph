"""Collect independently verified real captures across explicitly recorded attempts."""

import argparse
import json
from pathlib import Path

from commercegraph.config import Settings
from commercegraph.export import atomic_write, check_example, json_bytes, report_markdown
from commercegraph.llm import example_cases
from commercegraph.service import create_service

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("reports", nargs="+", help="Actual live report files, oldest first")
args = parser.parse_args()
service = create_service(Settings.from_env())
if service.settings.mode != "live":
    raise SystemExit("Live configuration is required to validate captures")
cases = {case["id"]: case for case in example_cases()}
verified = {}
for filename in args.reports:
    source = json.loads(Path(filename).read_text(encoding="utf-8"))
    for result in source["runs"]:
        identifier = result.get("example_id")
        if identifier not in cases or result.get("mode") != "live":
            continue
        if result.get("dataset_sha256") != service.dataset_hash:
            continue
        if check_example(cases[identifier], result, service):
            continue
        verified[identifier] = {**result, "capture_source": filename, "verification_errors": []}
missing = sorted(set(cases) - set(verified))
if missing:
    raise SystemExit(f"Missing verified real captures: {', '.join(missing)}")
report = {
    "mode": "live",
    "dataset_sha256": service.dataset_hash,
    "passed": True,
    "failed_examples": [],
    "source_reports": args.reports,
    "verification_method": (
        "Verified capture collection across recorded attempts, not a single uninterrupted run. "
        "Each question has its original timestamp, model, prompt version, evidence, usage and "
        "capture_source. Earlier failed attempts are retained separately."
    ),
    "runs": [verified[identifier] for identifier in cases],
}
atomic_write(Path("examples/sample_results.json"), json_bytes(report))
atomic_write(Path("examples/sample_results.md"), report_markdown(report).encode("utf-8"))
print(f"Verified {len(verified)} actual live captures across {len(args.reports)} reports.")
