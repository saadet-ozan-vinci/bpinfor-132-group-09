"""Stage: the human approval gate. Replaced in week 8.

Week 8 gates exactly one step, the irreversible one, with a LangGraph
`interrupt` and a checkpoint that a second process resumes. In this
application the irreversible step is submitting a case, and it reaches the
gate through one function:

    request_approval(payload: dict, unattended: bool) -> dict

`payload` has the shape of week 8's interrupt: `action`, `case_id`,
`arguments` (the exact arguments, never a summary a model wrote),
`evidence`, `degraded`, and `missing`. The return value has the shape of
week 8's resume value: `verdict` ("approve", "edit", "reject", or
"timeout"), `by`, and, for an edit, the edited `arguments`.

`unattended` is True in batch mode, which is how week 10 runs the
application. Nobody is there to answer, so your gate must return what week
8 decided an unanswered approval does after its timeout, immediately,
instead of waiting for a human who is not coming.

Until you wire yours in, the gate refuses every submission. That is the
safe default for a stub, and it means nothing irreversible can happen.

This is a stage you write rather than copy, because week 8's graph runs over
its own toy tools. Take your `submit` node from `labs/week08/starter/graph.py`
with its `interrupt` call, give it a small graph and a `SqliteSaver` of its
own, and write `request_approval` around it. Keep week 8's rule: above the
interrupt, read only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from project.trace import repo_root


def append(a: list, b: list) -> list:
    return a + b


class ApprovalState(TypedDict):
    payload: dict
    submitted: bool
    decision: str
    arguments: dict
    side_effects: Annotated[list[str], append]
    events: Annotated[list[str], append]


def approval_node(state: ApprovalState) -> dict:
    payload = state["payload"]
    resume = interrupt(payload)
    verdict = resume.get("verdict")
    if verdict == "approve":
        return {
            "submitted": True,
            "decision": "approve",
            "arguments": payload.get("arguments", {}),
            "side_effects": [f"SUBMITTED {payload['case_id']}"],
            "events": [f"gate:approve:{resume.get('by', '?')}"],
        }
    if verdict == "edit":
        arguments = resume.get("arguments") or payload.get("arguments", {})
        return {
            "submitted": True,
            "decision": "edit",
            "arguments": arguments,
            "side_effects": [f"SUBMITTED {payload['case_id']} (edited)"],
            "events": [f"gate:edit:{resume.get('by', '?')}"],
        }
    return {
        "submitted": False,
        "decision": verdict or "reject",
        "arguments": payload.get("arguments", {}),
        "side_effects": [],
        "events": [f"gate:{verdict or 'reject'}:{resume.get('by', '?')}"],
    }


def build_approval_graph(saver):
    graph = StateGraph(ApprovalState)
    graph.add_node("approval", approval_node)
    graph.add_edge(START, "approval")
    graph.add_edge("approval", END)
    return graph.compile(checkpointer=saver)


def request_approval(payload: dict, unattended: bool = False) -> dict:
    if unattended:
        return {"verdict": "timeout", "by": "system-timeout", "arguments": {}}

    db = repo_root() / "artifacts" / "week08_approvals.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "configurable": {
            "thread_id": f"{payload.get('action', 'approval')}:{payload['case_id']}",
        }
    }
    initial = {
        "payload": payload,
        "submitted": False,
        "decision": "",
        "arguments": payload.get("arguments", {}),
        "side_effects": [],
        "events": [],
    }
    with SqliteSaver.from_conn_string(str(db)) as saver:
        approval_graph = build_approval_graph(saver)
        out = approval_graph.invoke(initial, config)
        if "__interrupt__" in out:
            return {
                "verdict": "timeout",
                "by": "awaiting-human",
                "arguments": payload.get("arguments", {}),
            }
    return {
        "verdict": out.get("decision") or "reject",
        "by": "approval",
        "arguments": out.get("arguments", payload.get("arguments", {})),
    }
