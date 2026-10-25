"""Block 4, completed. TODO 8. One variant per group.

    python 02_stretch.py --variant model --replay
    python 02_stretch.py --variant voting --replay

The written answers are at the bottom.
"""

from __future__ import annotations

import argparse
import collections
import time

from queries import QUERIES
from router import Decision, apply_policy, classify
from scoring import report, score_routes

from project.models import LARGE, SMALL
from project.trace import write_json

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "compare_mod", Path(__file__).with_name("01_compare.py"))
_cmp = importlib.util.module_from_spec(_spec)
sys.modules["compare_mod"] = _cmp
_spec.loader.exec_module(_cmp)


# --------------------------------------------------------------------------
# TODO 8. One variant. Your instructor assigns you one.
# --------------------------------------------------------------------------

def variant_model(client) -> None:
    """Variant A. Same prompt, same queries, same policy. Only the model.

    Run the classifier over the twenty four queries on SMALL and on LARGE,
    score both, and report per route as counts.

    Report four things per model, not one:
      * route accuracy, and route accuracy excluding the ambiguous four
      * how often the evidence span came back verbatim
      * the minimum and maximum confidence, and how many distinct values
      * the resident memory, which is in project/models.py

    Predict which model wins before you run it, and write the prediction
    down. Then read the confidence range carefully. One of the two models
    tells you something about your threshold from TODO 3a that you cannot
    unsee.
    """
    #iterate through both models small and large
    for m in (SMALL, LARGE):
        routed_list= [] #init empty list that store final routing models for this model
        metas = []
        #iterating through queries
        for q in QUERIES:
            #call router to get a classification decision and metadata
            decisions, meta = classify(client, q.text , model = m.name)
            metas.append(meta)
            #pass recieved decision to the policy layer (confidence, evidence check, fallback)
            routed = apply_policy(decisions, q.text)
            #add to routed list with results
            routed_list.append(routed)
        #compare the predicted routes against the gold labels
        s = score_routes(routed_list, QUERIES)
        print(f"\n --------------- {m.name} ---------------")
        print(report(s, m.name))

        #get resident memory from models
        mem = m.resident_gb
        print(f"Resident memory: {mem} GB")
        if s.confidences:
            print(
                f"Classifier evidence verified: {s.evidence_ok}/{s.total}; "
                f"confidence min {min(s.confidences):.2f}, "
                f"max {max(s.confidences):.2f}, "
                f"distinct {len(set(s.confidences))}"
            )
        print(
            f"Classifier tokens: "
            f"{sum(x['prompt_tokens'] + x['completion_tokens'] for x in metas)}"
        )


def variant_voting(client, k: int = 3) -> None:
    """Variant B. Classify k times at temperature 0.7, majority wins.

    Run sequentially rather than in threads. Your endpoint answers one
    request at a time, so a thread pool buys you nothing here, and finding
    that out is worth more than the speedup you expected.

    Score the majority result, but the number to report is not the accuracy.
    It is the set of queries where the k votes disagreed. Print it, and put
    it next to the list of ambiguous query ids.

    Then ask what that set is worth. Voting costs k times as much for a step
    that was already the cheap one, so as a way to decide it is a poor buy.
    As a way to detect something, it may be a very good one.
    """
    if k < 1 or k % 2 == 0:
        raise ValueError("k must be a positive odd number")

    voted_results = []
    disagreements = []
    total_tokens = 0
    for query in QUERIES:
        ballot: list[str | None] = []
        decisions: list[Decision | None] = []
        for _ in range(k):
            decision, meta = classify(
                client, query.text, model=SMALL.name, temperature=0.7)
            decisions.append(decision)
            ballot.append(decision.route if decision is not None else None)
            total_tokens += meta["prompt_tokens"] + meta["completion_tokens"]

        if len(set(ballot)) > 1:
            disagreements.append({
                "query_id": query.id,
                "votes": ballot,
            })

        counts = collections.Counter(ballot)
        winning_count = max(counts.values())
        winning_route = next(
            route for route in ballot if counts[route] == winning_count)
        if winning_route is None:
            winning_decision = None
        else:
            winning_decisions = [
                decision for decision in decisions
                if decision is not None and decision.route == winning_route
            ]
            representative = winning_decisions[0]
            average_confidence = sum(
                decision.confidence for decision in winning_decisions
            ) / len(winning_decisions)
            winning_decision = representative.model_copy(
                update={"confidence": average_confidence})

        voted_results.append(apply_policy(winning_decision, query.text))

    scoreboard = score_routes(voted_results, QUERIES)
    print(report(scoreboard, "majority vote"))
    ambiguous_ids = [query.id for query in QUERIES if query.ambiguous]
    print(f"disagreement queries ({len(disagreements)}): {disagreements}")
    print(f"ambiguous query ids: {ambiguous_ids}")
    print(f"classifier tokens across {len(QUERIES) * k} calls: {total_tokens}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("model", "voting"), required=True)
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = _cmp.get_client(args.replay)
    if args.variant == "model":
        variant_model(client)
    else:
        variant_voting(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
