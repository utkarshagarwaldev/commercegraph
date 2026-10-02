"""Verify selected real cases without claiming a complete submission report."""

import argparse
import json
from dataclasses import replace
from pathlib import Path
from time import sleep

from commercegraph.config import Settings
from commercegraph.export import check_example
from commercegraph.llm import example_cases
from commercegraph.service import create_service

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("ids", nargs="+", help="Example IDs such as Q01 Q05 Q14")
parser.add_argument("--output", default="examples/targeted_live_results.json")
args = parser.parse_args()
cases = [case for case in example_cases() if case["id"] in args.ids]
if set(args.ids) != {case["id"] for case in cases}:
    raise SystemExit("Unknown example ID")
settings = replace(Settings.from_env(), mode="live", dataset_path=None)
service = create_service(settings)
runs = []
for index, case in enumerate(cases):
    if index:
        sleep(15)
    print(f"Running {case['id']}", flush=True)
    result = service.ask(case["question"])
    result["example_id"] = case["id"]
    result["verification_errors"] = check_example(case, result, service)
    runs.append(result)
    print(
        json.dumps(
            {
                "id": case["id"],
                "status": result["status"],
                "source": result["answer_presentation_source"],
                "errors": result["verification_errors"],
            }
        ),
        flush=True,
    )
report = {
    "scope": "selected cases only",
    "passed": all(not r["verification_errors"] for r in runs),
    "runs": runs,
}
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
raise SystemExit(0 if report["passed"] else 1)
