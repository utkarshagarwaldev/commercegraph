"""Explicit opt-in checks use both real Gemini stages and independent expected facts."""

import os
from dataclasses import replace
from time import sleep

import pytest

from commercegraph.config import Settings
from commercegraph.export import check_example
from commercegraph.llm import example_cases
from commercegraph.service import create_service


def configured_live_service():
    settings = Settings.from_env()
    if not settings.api_key:
        pytest.fail("GEMINI_API_KEY is required for opted-in live verification")
    return create_service(replace(settings, mode="live", dataset_path=None))


@pytest.fixture(scope="module")
def live_service():
    if os.getenv("RUN_LIVE_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_TESTS=1 to authorize real Gemini integration tests")
    interval = float(os.getenv("LIVE_TEST_INTERVAL_SECONDS", "15"))
    if not 0 <= interval <= 60:
        pytest.fail("LIVE_TEST_INTERVAL_SECONDS must be between 0 and 60")
    return configured_live_service(), interval, {"completed": 0}


@pytest.mark.live
@pytest.mark.parametrize("case", example_cases(), ids=lambda case: case["id"])
def test_live_pipeline(case, live_service):
    service, interval, state = live_service
    if state["completed"]:
        sleep(interval)
    result = service.ask(case["question"])
    state["completed"] += 1
    assert not check_example(case, result, service), result
