"""Produce one OpenTelemetry trace covering retry, fallback, and the gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from faults import FaultPlan
from graph import build, initial
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from retry import StepPolicy, call_with_policy
import tools


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "trace_homework.json"


def main() -> int:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("week08.homework")

    def traced_fallback(plan: FaultPlan, topic: str):
        with tracer.start_as_current_span("week08.fallback") as fallback_span:
            value = tools.keyword_fallback(plan, topic)
            fallback_span.set_attribute("items", len(value))
            return value

    with tracer.start_as_current_span("week08.retry") as span:
        plan = FaultPlan.parse("search:server_error@1.0")
        result = call_with_policy(
            tools.search,
            plan,
            "parking vignette",
            policy=StepPolicy(
                attempts=3, base_delay=0.0, jitter=False, max_elapsed=1.0
            ),
            fallback=traced_fallback,
        )
        span.set_attribute("outcome", result.outcome)
        span.set_attribute("attempts", result.tries)
        span.set_attribute("fallback", result.used_fallback)

    with tracer.start_as_current_span("week08.gate") as span:
        db = ":memory:"
        config = {"configurable": {"thread_id": "trace-homework"}}
        with SqliteSaver.from_conn_string(db) as saver:
            graph = build(FaultPlan.parse(""), saver)
            paused = graph.invoke(
                initial("trace-homework", "parking vignette"), config
            )
            payload = paused["__interrupt__"][0].value
            span.set_attribute("paused", True)
            span.set_attribute("action", payload["action"])
            result = graph.invoke(
                Command(resume={"verdict": "timeout", "by": "system-timeout"}),
                config,
            )
            span.set_attribute("submitted", result["submitted"])
            span.set_attribute("decision", result["decision"])

    spans = [
        {
            "name": item.name,
            "attributes": dict(item.attributes),
            "status": item.status.status_code.name,
        }
        for item in exporter.get_finished_spans()
    ]
    OUTPUT.write_text(json.dumps({"spans": spans}, indent=2) + "\n")
    print(f"trace written to {OUTPUT}")
    print("spans: " + ", ".join(item["name"] for item in spans))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
