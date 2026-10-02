"""Escaped downloads and reports generated only from actual service executions."""

import csv
import io
import json
import os
import tempfile
from pathlib import Path

from commercegraph.llm import example_cases
from commercegraph.models import make_query
from commercegraph.resolution import resolve_plan


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _csv_cell(value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and (
        value.startswith(("\t", "\r")) or value.lstrip().startswith(("=", "+", "-", "@"))
    ):
        value = "'" + value
    return value


def records_csv(records: list[dict]) -> bytes:
    rows = [{"record_id": record["record_id"], **record["fields"]} for record in records]
    columns = sorted({key for row in rows for key in row}) or ["record_id"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows({key: _csv_cell(value) for key, value in row.items()} for row in rows)
    return output.getvalue().encode("utf-8-sig")


def graph_export(graph) -> dict:
    return {
        "export_schema_version": 1,
        "attributes": dict(graph.graph),
        "nodes": [
            {"key": key, "attributes": dict(attrs)} for key, attrs in sorted(graph.nodes(data=True))
        ],
        "edges": [
            {"source": source, "target": target, "attributes": dict(attrs)}
            for source, target, attrs in sorted(graph.edges(data=True))
        ],
    }


def check_example(case: dict, result: dict, service) -> list[str]:
    errors = []
    if result["status"] != case["status"]:
        errors.append(f"Expected status {case['status']}; got {result['status']}")
    if case["status"] in {"ok", "no_data"}:
        evidence = result.get("evidence") or {}
        fields = [record["fields"] for record in evidence.get("records", [])]
        if [field["id"] for field in fields] != case["ids"]:
            errors.append("Retrieved IDs differ from independent fixture expectations")
        if evidence.get("aggregates", {}).get("matching_count") != len(case["ids"]):
            errors.append("Matching count differs from independent fixture expectation")
        for expected_key, field in [
            ("prices_paise", "price_paise"),
            ("totals_paise", "total_paise"),
            ("counts", "product_count"),
            ("product_ids", "product_id"),
            ("order_statuses", "status"),
        ]:
            if expected_key in case and [f.get(field) for f in fields] != case[expected_key]:
                errors.append(f"Mismatch in {expected_key}")
        expected = resolve_plan(service.graph, make_query(case["operation"], **case["parameters"]))
        if result.get("resolved_plan") != expected.model_dump(exclude_none=True):
            errors.append("Interpreted operation or filters differ from expected intent")
        if service.settings.mode == "live" and result.get("answer_presentation_source") != "gemini":
            errors.append("Both real Gemini stages must succeed for the submission examples")
    return errors


def report_markdown(report: dict) -> str:
    lines = [
        f"# CommerceGraph actual {report['mode']} execution report",
        "",
        "Offline fixtures do not demonstrate real LLM integration."
        if report["mode"] == "offline"
        else "These results were captured from the real Gemini pipeline.",
        "",
    ]
    if report.get("verification_method"):
        lines.extend([report["verification_method"], ""])
    for run in report["runs"]:
        lines.extend(
            [
                f"## {run['example_id']}",
                "",
                run["question"],
                "",
                f"Status: `{run['status']}` · presentation: `{run['answer_presentation_source']}`",
                "",
                "```text",
                run["answer"].replace("```", "'''"),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def atomic_write(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(prefix=".report-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as output:
            output.write(content)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def export_examples(
    service, directory: str | Path, on_example=None, interval_seconds=0
) -> tuple[dict, Path]:
    if not 0 <= interval_seconds <= 60:
        raise ValueError("Example interval must be between 0 and 60 seconds")
    from time import sleep

    runs, failures = [], []
    for index, case in enumerate(example_cases()):
        if index and interval_seconds:
            sleep(interval_seconds)
        if on_example:
            on_example(case["id"])
        result = service.ask(case["question"])
        result["example_id"] = case["id"]
        result["verification_errors"] = check_example(case, result, service)
        runs.append(result)
        if result["verification_errors"]:
            failures.append(case["id"])
    report = {
        "mode": service.settings.mode,
        "dataset_sha256": service.dataset_hash,
        "passed": not failures,
        "failed_examples": failures,
        "runs": runs,
    }
    directory = Path(directory)
    if failures:
        path = directory / f"{service.settings.mode}_failures.json"
        atomic_write(path, json_bytes(report))
    else:
        name = "sample_results" if service.settings.mode == "live" else "offline_results"
        path = directory / f"{name}.json"
        atomic_write(path, json_bytes(report))
        atomic_write(directory / f"{name}.md", report_markdown(report).encode("utf-8"))
    return report, path
