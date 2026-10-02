"""Read-only access diagnostic. Provider messages are redacted before display."""

import argparse
import json
import re
import ssl
from dataclasses import replace

import httpx
from google import genai
from google.genai import errors, types

from commercegraph.config import Settings
from commercegraph.models import QueryPlan
from commercegraph.prompts import PLANNER_INSTRUCTIONS
from commercegraph.resolution import catalog
from commercegraph.service import create_service

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tls12", action="store_true", help="Use verified TLS 1.2 for diagnosis")
parser.add_argument("--question", help="Diagnose the actual query planner with the sample catalog")
args = parser.parse_args()
settings = Settings.from_env()
if not settings.api_key:
    raise SystemExit("GEMINI_API_KEY is not configured")
client_args = {}
if args.tls12 or settings.tls12:
    context = ssl.create_default_context()
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    client_args["verify"] = context
client = genai.Client(
    api_key=settings.api_key,
    http_options=types.HttpOptions(timeout=30000, client_args=client_args),
)
try:
    response = client.models.generate_content(
        model=settings.model,
        contents=(
            json.dumps(
                {
                    "question": args.question,
                    "entity_catalog": catalog(
                        create_service(replace(settings, dataset_path=None)).graph
                    ),
                }
            )
            if args.question
            else "Return an unsupported plan for the capital of France question."
        ),
        config=types.GenerateContentConfig(
            system_instruction=PLANNER_INSTRUCTIONS if args.question else None,
            response_mime_type="application/json",
            response_json_schema=QueryPlan.model_json_schema(),
            max_output_tokens=4096,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    print(
        json.dumps(
            {
                "status": "received",
                "model": response.model_version,
                "finish_reason": str(response.candidates[0].finish_reason),
            },
            indent=2,
        )
    )
except errors.APIError as error:
    message = str(getattr(error, "message", "API request failed"))
    message = message.replace(settings.api_key, "[REDACTED]")
    message = re.sub(r"AIza[A-Za-z0-9_-]+", "[REDACTED]", message)
    print(
        json.dumps(
            {"status": "api_error", "http_code": error.code, "message": message[:1000]}, indent=2
        )
    )
    raise SystemExit(1)
except (httpx.HTTPError, TimeoutError, OSError) as error:
    print(
        json.dumps(
            {
                "status": "connection_error",
                "error_type": type(error).__name__,
                "message": "Could not establish the Gemini HTTPS connection; no plan received.",
            },
            indent=2,
        )
    )
    raise SystemExit(1)
