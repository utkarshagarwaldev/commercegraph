"""One orchestration service shared by CLI and UI."""

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

import networkx as nx

from commercegraph.answers import default_answer_plan, render_answer, validate_answer_plan
from commercegraph.config import Settings
from commercegraph.dataset import load_dataset
from commercegraph.graph import build_graph
from commercegraph.llm import FixtureProvider, GeminiProvider, LLMError, Provider
from commercegraph.models import QueryPlan
from commercegraph.prompts import PROMPT_VERSION
from commercegraph.queries import execute_query
from commercegraph.resolution import ResolutionError, catalog, resolve_plan

MESSAGES = {
    "missing_entity": "Name the entity to query, such as a product, brand, customer, or order ID.",
    "ambiguous_entity": "Use a canonical entity name or ID to clarify the match.",
    "incomplete_question": "Ask a standalone question naming entities and supported constraints.",
    "out_of_scope": "This question is outside the sample commerce graph's supported scope.",
    "unsupported_constraint": "Constraint unsupported. Inspect the supported query types.",
    "missing_fact": "The sample graph does not contain the facts needed for this question.",
}


@dataclass
class CommerceService:
    graph: nx.DiGraph
    dataset_hash: str
    provider: Provider
    settings: Settings

    def ask(self, question: str, on_stage=None) -> dict:
        start = perf_counter()
        result = {
            "question": question,
            "mode": self.settings.mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": self.settings.model if self.settings.mode == "live" else "offline-fixture",
            "dataset_sha256": self.dataset_hash,
            "prompt_version": PROMPT_VERSION,
            "raw_plan": None,
            "resolved_plan": None,
            "status": "invalid_plan",
            "evidence": None,
            "answer": "",
            "answer_plan": None,
            "answer_presentation_source": None,
            "stage_durations_seconds": {},
            "token_usage": {},
            "error_code": None,
        }

        def stage(label):
            if on_stage:
                on_stage(label)

        try:
            if not isinstance(question, str) or not question.strip() or len(question) > 1000:
                raise ValueError("Enter a question of 1–1000 characters.")
            stage("Interpreting the question")
            mark = perf_counter()
            reply = self.provider.plan_query(question, catalog(self.graph))
            result["raw_plan"] = reply.raw_plan or reply.value.model_dump()
            plan = QueryPlan.model_validate(reply.value.model_dump())
            result["stage_durations_seconds"]["interpret"] = perf_counter() - mark
            result["token_usage"]["query"] = reply.usage
            result["model"] = reply.model or result["model"]
            if plan.decision != "query":
                result["status"] = (
                    "clarification_required" if plan.decision == "clarify" else "unsupported"
                )
                result["answer"] = MESSAGES[plan.clarification_code or plan.unsupported_code]
                return result
            stage("Retrieving graph evidence")
            mark = perf_counter()
            resolved = resolve_plan(self.graph, plan)
            result["resolved_plan"] = resolved.model_dump(exclude_none=True)
            bundle = execute_query(self.graph, resolved)
            result["evidence"] = bundle.model_dump(mode="json")
            result["stage_durations_seconds"]["retrieve"] = perf_counter() - mark
            result["status"] = bundle.status
            stage("Preparing the answer")
            mark = perf_counter()
            try:
                reply = self.provider.plan_answer(question, result["resolved_plan"], bundle)
                result["token_usage"]["answer"] = reply.usage
                result["raw_answer_plan"] = reply.raw_plan or reply.value.model_dump()
                answer_plan = validate_answer_plan(reply.value, bundle)
                result["answer_presentation_source"] = (
                    "gemini" if self.settings.mode == "live" else "offline-fixture"
                )
            except (LLMError, ValueError) as error:
                answer_plan = default_answer_plan(bundle)
                result["answer_presentation_source"] = "deterministic_fallback"
                result["presentation_error_code"] = getattr(error, "code", "invalid_answer_plan")
            result["answer_plan"] = answer_plan.model_dump()
            result["answer"] = render_answer(answer_plan, bundle)
            result["stage_durations_seconds"]["present"] = perf_counter() - mark
        except ResolutionError as error:
            result.update(status=error.status, answer=str(error))
        except LLMError as error:
            status = "invalid_plan" if error.code == "invalid_plan" else "llm_unavailable"
            result.update(status=status, answer=str(error), error_code=error.code)
        except ValueError:
            result.update(
                status="invalid_plan", answer="Question or interpretation failed validation."
            )
        finally:
            result["duration_seconds"] = perf_counter() - start
        return result


def create_service(settings: Settings | None = None, provider: Provider | None = None):
    settings = settings or Settings.from_env()
    dataset, digest = load_dataset(settings.dataset_path)
    graph = build_graph(dataset)
    if provider is None:
        provider = GeminiProvider(settings) if settings.mode == "live" else FixtureProvider()
    return CommerceService(graph, digest, provider, settings)
