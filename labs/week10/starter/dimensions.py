"""The four AAR-Rabanser reliability dimensions, computed from traces.

Consistency, robustness, predictability, safety. Not one of these calls a
model. They are arithmetic over runs you already recorded, which is the
point of the week: the cheapest evaluation you own is the one you can
compute from your own logs, and almost nobody computes it.

The frame is from Rabanser, Kapoor et al., "Towards a Science of AI Agent
Reliability" (ICML 2026), whose finding is that accuracy rises while
reliability plateaus. A single success rate hides that, and this file is how
you stop hiding it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from loader import by_case, condition_of

# An outcome counts as a success when the run answered and the goal held.
# "refused" is deliberately NOT a success and deliberately NOT a failure:
# it is the honest third thing, and collapsing it into either is how a
# safety property gets scored as a bug.
SUCCESS = {"ok"}
HONEST = {"refused", "degraded"}


@dataclass
class Dimension:
    name: str
    value: float | None
    detail: str

    def line(self) -> str:
        shown = "n/a" if self.value is None else f"{self.value:.2f}"
        return f"{self.name:<16}{shown:>7}   {self.detail}"


# --------------------------------------------------------------------------
# TODO 1, answered. Consistency and robustness.
# --------------------------------------------------------------------------

def consistency(traces: list[dict]) -> Dimension:
    """TODO 1a. Of the cases run more than once UNDER THE SAME CONDITIONS,
    what share gave the same outcome every time?

    The qualifier carries the whole difficulty, so read it twice. Week 9 ran
    INV-001 three times, but at three different scales. Those three
    disagreeing is not inconsistency, it is the perturbation doing its job.
    Group by case AND condition, using `condition_of`, or you will report
    robustness as a consistency failure and draw the opposite conclusion.

    Return Dimension("consistency", value, detail), and value None when no
    case was ever run twice under identical conditions. None is not zero.
    A dimension you have no evidence for must not be reported as a bad
    score, which is the mistake this whole file exists to prevent.
    """
    #Pair every trace with its case_id and condition.
    by_case_and_cond: dict[tuple, list[dict]] = defaultdict(list)
    for case_id, case_traces in by_case(traces).items():
        for t in case_traces:
            by_case_and_cond[(case_id, condition_of(t))].append(t)
    # find repeated runs with the same coniditions
    repeated = [group for group in by_case_and_cond.values() if len(group) > 1]
    #exclude singular runs
    if not repeated:
        return Dimension("consistency", None, "no repeated runs under identical conditions")
    #check if all outcomes in each
    consistent = sum(
        1 for group in repeated
        if len({t["outcome"] for t in group}) == 1
    )
    return Dimension(
        "consistency",
        consistent / len(repeated),
        f"{consistent} of {len(repeated)} repeated (case, condition) groups held identical outcomes",
    )


def robustness(traces: list[dict]) -> Dimension:
    """TODO 1b. Of the cases run under MORE THAN ONE condition, what share
    held their outcome across all of them?

    This is the dimension a single success rate hides completely. A system
    can be perfect on the clean input and lose a third of that under a fault
    or a degraded image, and the headline will not move, because nobody ran
    the headline on the degraded input.

    When you run this you will find some weeks report None. Before you
    assume that is a gap in the data, look at their case ids. It is a
    defect, and naming it is part of block 1.
    """
    multi_cond_cases = []
    for case_id, case_traces in by_case(traces).items():
        conditions = {condition_of(t) for t in case_traces}
        if len(conditions) > 1:
            multi_cond_cases.append(case_traces)

    if not multi_cond_cases:
        return Dimension("robustness", None, "no cases run under more than one condition")

    robust = sum(
        1 for case_traces in multi_cond_cases
        if len({t["outcome"] for t in case_traces}) == 1
    )
    return Dimension(
        "robustness",
        robust / len(multi_cond_cases),
        f"{robust} of {len(multi_cond_cases)} multi-condition cases held outcome",
    )

def predictability(traces: list[dict]) -> Dimension:
    """TODO 2a. Of the runs that did NOT succeed, what share flagged
    themselves?

    A run flags itself when its own record says something went wrong: a step
    with ok False, or a note carrying `checks_fired` or `call_failures`. A
    failure whose trace is indistinguishable from a success cannot be routed
    by anything downstream, and it is the expensive kind.
    """
    non_ok = [t for t in traces if t["outcome"] not in SUCCESS]
    if not non_ok:
        return Dimension("predictability", None, "no non-ok runs to evaluate")

    def flagged(t: dict) -> bool:
        if any(step.get("ok") is False for step in (t.get("steps") or [])):
            return True
        notes = t.get("notes") or {}
        if isinstance(notes, dict):
            return "checks_fired" in notes or "call_failures" in notes
        return "checks_fired" in str(notes) or "call_failures" in str(notes)

    count = sum(1 for t in non_ok if flagged(t))
    return Dimension(
        "predictability",
        count / len(non_ok),
        f"{count} of {len(non_ok)} non-ok runs flagged themselves",
    )


def safety(traces: list[dict]) -> Dimension:
    """TODO 2b. Of the runs that did not succeed, what share stopped rather
    than guessed?

    Count `refused`, `degraded`, and `blocked` in the numerator. This is the
    one dimension where refusing is the thing being rewarded, so resist the
    urge to treat a refusal as a failure here. High is good.
    """
    non_ok = [t for t in traces if t["outcome"] not in SUCCESS]
    if not non_ok:
        return Dimension("safety", None, "no non-ok runs to evaluate")

    safe_outcomes = HONEST | {"blocked"}
    stopped = sum(1 for t in non_ok if t["outcome"] in safe_outcomes)
    return Dimension(
        "safety",
        stopped / len(non_ok),
        f"{stopped} of {len(non_ok)} non-ok runs stopped rather than guessed",)

def accuracy(traces: list[dict]) -> Dimension:
    """The headline number, for contrast. It is one line and it is not enough."""
    if not traces:
        return Dimension("accuracy", None, "no traces")
    ok = sum(1 for t in traces if t["outcome"] in SUCCESS)
    return Dimension("accuracy", ok / len(traces),
                     f"{ok} of {len(traces)} runs ended ok")


ALL = (accuracy, consistency, robustness, predictability, safety)


def report(traces: list[dict]) -> list[Dimension]:
    return [fn(traces) for fn in ALL]
