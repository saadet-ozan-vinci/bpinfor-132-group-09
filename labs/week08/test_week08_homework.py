"""Homework checks for the week08 timeout and unattended gate."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "starter"))

from faults import ContractDrift, FaultPlan  # noqa: E402
from graph import build, initial  # noqa: E402
from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402
from langgraph.types import Command  # noqa: E402
from retry import StepPolicy, call_with_policy, is_retryable  # noqa: E402
import tools  # noqa: E402


def test_contract_drift_is_not_retried() -> None:
    result = call_with_policy(
        lambda: (_ for _ in ()).throw(ContractDrift("renamed field")),
        policy=StepPolicy(attempts=3, base_delay=0.0, jitter=False),
    )
    assert not is_retryable(ContractDrift())
    assert result.tries == 1
    assert result.outcome == "degraded"


def test_fallback_is_recorded() -> None:
    plan = FaultPlan.parse("search:server_error@1.0")
    result = call_with_policy(
        tools.search,
        plan,
        "parking vignette",
        policy=StepPolicy(attempts=2, base_delay=0.0, jitter=False),
        fallback=tools.keyword_fallback,
    )
    assert result.used_fallback
    assert result.outcome == "fallback"


def test_unanswered_gate_rejects_without_submitting(tmp_path: Path) -> None:
    db = tmp_path / "gate.sqlite"
    config = {"configurable": {"thread_id": "timeout-test"}}
    with SqliteSaver.from_conn_string(str(db)) as saver:
        graph = build(FaultPlan.parse(""), saver)
        paused = graph.invoke(
            initial("timeout-test", "parking vignette"), config
        )
        assert paused["__interrupt__"][0].value["action"] == "submit_case"
        result = graph.invoke(
            Command(resume={"verdict": "timeout", "by": "system-timeout"}),
            config,
        )
    assert result["submitted"] is False
    assert result["decision"] == "timeout"
    assert result["side_effects"] == []
