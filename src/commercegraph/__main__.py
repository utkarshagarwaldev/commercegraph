"""CLI commands share the application's retrieval and grounding service."""

import argparse
import json
import sys
from dataclasses import replace

from commercegraph.config import Settings
from commercegraph.export import export_examples
from commercegraph.graph import validate_graph
from commercegraph.service import create_service


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="commercegraph")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Validate source, graph relationships and marker audit")
    ask = commands.add_parser("ask", help="Ask the same service used by the UI")
    ask.add_argument("question")
    ask.add_argument("--mode", choices=["live", "offline"])
    ask.add_argument("--json", action="store_true", help="Print complete execution evidence")
    export = commands.add_parser("export-examples", help="Run and verify the predefined examples")
    export.add_argument("--mode", choices=["live", "offline"], required=True)
    export.add_argument("--output", default="examples")
    export.add_argument(
        "--interval-seconds",
        type=float,
        default=0,
        help="Pause between example questions (0–60 seconds) to respect API limits",
    )
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if getattr(args, "mode", None):
            settings = replace(settings, mode=args.mode)
        service = create_service(settings)
        if args.command == "validate":
            print(
                json.dumps(
                    {**validate_graph(service.graph), "dataset_sha256": service.dataset_hash},
                    indent=2,
                )
            )
            return 0
        if args.command == "ask":
            result = service.ask(args.question)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"Mode: {result['mode']} | Status: {result['status']}")
                print(result["answer"])
                print(f"Presentation: {result['answer_presentation_source'] or 'no answer stage'}")
            return (
                0
                if result["status"]
                in {"ok", "no_data", "unsupported", "clarification_required", "entity_not_found"}
                else 1
            )
        if settings.mode == "live" and not settings.api_key:
            print("GEMINI_API_KEY is missing; no live report was written.", file=sys.stderr)
            return 1
        report, path = export_examples(
            service,
            args.output,
            on_example=lambda x: print(f"Running {x}"),
            interval_seconds=args.interval_seconds,
        )
        print(f"{'Passed' if report['passed'] else 'Failed'}: {path}")
        return 0 if report["passed"] else 1
    except (ValueError, OSError):
        print(
            "Dataset/configuration error. Check JSON schema, references, and marker audit.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
