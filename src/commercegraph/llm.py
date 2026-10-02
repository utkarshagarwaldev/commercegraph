"""Real Gemini structured output adapter, with separately labeled fixture demonstrations."""

import json
import ssl
from dataclasses import dataclass
from importlib.resources import files
from typing import Protocol

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from commercegraph.answers import default_answer_plan, expected_template
from commercegraph.config import Settings
from commercegraph.models import RULES, AnswerPlan, Parameters, QueryPlan, make_query
from commercegraph.prompts import ANSWER_INSTRUCTIONS, PLANNER_INSTRUCTIONS


class LLMError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ModelReply:
    value: BaseModel
    usage: dict | None = None
    model: str | None = None
    raw_plan: dict | None = None


class Provider(Protocol):
    def plan_query(self, question: str, catalog: dict) -> ModelReply: ...
    def plan_answer(self, question: str, query: dict, evidence) -> ModelReply: ...


class GeminiProvider:
    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        self.client = client

    def _generate(self, schema, system: str, payload: dict) -> ModelReply:
        if not self.settings.api_key and self.client is None:
            raise LLMError("missing_key", "Set GEMINI_API_KEY in your local .env to ask Gemini.")
        if self.client is None:
            client_args = {}
            if self.settings.tls12:
                context = ssl.create_default_context()
                context.maximum_version = ssl.TLSVersion.TLSv1_2
                client_args["verify"] = context
            self.client = genai.Client(
                api_key=self.settings.api_key,
                http_options=types.HttpOptions(
                    timeout=30000,
                    client_args=client_args,
                    retry_options=types.HttpRetryOptions(attempts=2, initial_delay=1, max_delay=3),
                ),
            )
        try:
            response = self.client.models.generate_content(
                model=self.settings.model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_json_schema=schema.model_json_schema(),
                    max_output_tokens=4096,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            candidates = response.candidates or []
            if not candidates:
                raise LLMError("refusal", "Gemini did not provide a usable answer candidate.")
            reason = getattr(candidates[0].finish_reason, "value", candidates[0].finish_reason)
            if reason != "STOP":
                code = "incomplete" if reason == "MAX_TOKENS" else "refusal"
                raise LLMError(code, "Gemini's response was incomplete or blocked; try rephrasing.")
            if not response.text:
                raise LLMError("empty_response", "Gemini returned no structured response.")
            # Validate locally rather than trusting SDK parsing or schema constraints alone.
            raw = json.loads(response.text)
            value = schema.model_validate(raw)
            usage = response.usage_metadata
            return ModelReply(
                value=value,
                usage=usage.model_dump(mode="json", exclude_none=True) if usage else None,
                model=response.model_version or self.settings.model,
                raw_plan=raw,
            )
        except (ValidationError, json.JSONDecodeError) as error:
            raise LLMError(
                "invalid_plan", "Gemini's plan violated the query or answer contract."
            ) from error
        except errors.APIError as error:
            code = error.code
            if code == 429:
                message = (
                    "Gemini quota or rate limit reached. Check AI Studio limits and retry later."
                )
            elif code in {401, 403}:
                message = "Gemini rejected API access. Check the local key and account permissions."
            elif code == 404:
                message = "Gemini model unavailable. Set GEMINI_MODEL to an accessible model."
            elif code == 503:
                message = "Gemini model is busy. Retry later or configure another supported model."
            else:
                message = (
                    "Gemini request failed. Check connectivity and provider status, then retry."
                )
            # Do not expose provider exception strings: URLs or bodies may contain credentials.
            raise LLMError(f"api_{code}", message) from error
        except (httpx.HTTPError, TimeoutError, OSError) as error:
            raise LLMError(
                "connection", "Gemini connection failed or timed out. Retry when connected."
            ) from error

    def plan_query(self, question: str, catalog: dict) -> ModelReply:
        return self._generate(
            QueryPlan,
            PLANNER_INSTRUCTIONS,
            {
                "question": question,
                "entity_catalog": catalog,
                "operation_input_contracts": {
                    name: {"required": sorted(required), "allowed": sorted(allowed)}
                    for name, (required, allowed) in RULES.items()
                },
            },
        )

    def plan_answer(self, question: str, query: dict, evidence) -> ModelReply:
        return self._generate(
            AnswerPlan,
            ANSWER_INSTRUCTIONS,
            {
                "question": question,
                "query": query,
                "allowed_template": expected_template(evidence),
                "records": [
                    {"record_id": r.record_id, "fields": r.fields} for r in evidence.records
                ],
                "aggregates": evidence.aggregates,
                "required_record_ids": [r.record_id for r in evidence.records],
                "required_aggregate_keys": list(evidence.aggregates),
            },
        )


def example_cases() -> list[dict]:
    return json.loads(files("commercegraph").joinpath("data/questions.json").read_text("utf-8"))


class FixtureProvider:
    """Exact predefined demonstrations only. This is not natural-language inference."""

    def plan_query(self, question: str, catalog: dict) -> ModelReply:
        case = next((c for c in example_cases() if c["question"] == question), None)
        if case is None:
            raise LLMError(
                "offline_question", "Offline mode supports the predefined examples only."
            )
        if "operation" in case:
            plan = make_query(case["operation"], **case["parameters"])
        else:
            plan = QueryPlan(
                decision=case["decision"],
                operation=None,
                parameters=Parameters(**dict.fromkeys(Parameters.model_fields)),
                clarification_code=case.get("clarification_code"),
                unsupported_code=case.get("unsupported_code"),
            )
        return ModelReply(plan, model="offline-fixture", raw_plan=plan.model_dump())

    def plan_answer(self, question: str, query: dict, evidence) -> ModelReply:
        plan = default_answer_plan(evidence)
        return ModelReply(plan, model="offline-fixture", raw_plan=plan.model_dump())
