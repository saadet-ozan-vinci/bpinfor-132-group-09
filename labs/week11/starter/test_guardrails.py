"""Block 3: gates. Week 10 built the harness, this is what week 11 adds.

Every gate here asserts a PROPERTY that should hold for any healthy version
of the guard stack, never a number this week happened to produce. A gate
pinned to "catches 7 of 9" fails the first time somebody adds a pattern.

    pytest -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project_spine"))

from guards import GUARDS, Guard, Verdict
from traffic import ATTACKS, LEGIT

from project.contracts import GuardEvent

from project.trace import repo_root

EVENTS = repo_root() / "artifacts" / "guard_events.jsonl"


def test_every_guard_declares_placement_action_and_fail_mode():
    """An undeclared fail mode is a decision somebody makes at 3am."""
    for name, guard in GUARDS.items():
        assert guard.placement in {"pre_model", "post_model", "pre_action"}
        assert guard.action in {"allow", "flag", "block", "rewrite"}
        assert guard.fail_mode in {"open", "closed"}, (
            f"{name} has no declared fail mode")


def test_a_guard_that_raises_does_not_propagate():
    """A control that takes the request down with it has turned a detection
    problem into an availability problem."""
    def broken(_text):
        raise RuntimeError("boom")
    for mode in ("open", "closed"):
        guard = Guard("broken", "pre_model", "block", mode, broken)
        verdict, _, triggered = guard.run("hello")
        assert triggered is True
        assert verdict.fired is (mode == "closed")


def test_false_block_rate_is_bounded():
    """TODO 4a. The gate nobody writes.

    A guard measured only on attacks can score perfectly by blocking
    everything. Assert a bound on how many LEGITIMATE messages each guard
    blocks, and pick the bound deliberately: zero is a defensible choice
    and so is one, but you have to say which and why in DECISIONS.md.
    """
    raise NotImplementedError("TODO 4a")


def test_no_single_guard_is_both_the_best_and_the_cheapest():
    """TODO 4b. The trade-off, asserted rather than asserted-about.

    For each guard compute (attacks caught, legitimate messages blocked).
    Then assert that no single guard both catches the most AND blocks
    nobody. If one does, the rest of your stack is pure added latency and
    you should delete it.

    Expect this to be uncomfortable. On this corpus layering does NOT
    raise the catch rate, so a gate demanding that would fail and would be
    right to. What layering buys here is that the best catcher is also the
    only one with a false block.
    """
    raise NotImplementedError("TODO 4b")


def test_the_pre_action_layer_prevents_what_input_layers_only_detect():
    """Catch rate does not distinguish detection from prevention.

    An input guard that fires has detected an attack in prose. The
    pre_action guard fires on a tool argument, which is the last point at
    which anything can still be stopped. Assert it covers the attacks that
    actually reach for a tool.
    """
    guard = GUARDS["tool_argument"]
    tool_seeking = [a for a in ATTACKS
                    if any(w in a.text.lower()
                           for w in ("admin passwords", "system prompt"))]
    assert tool_seeking, "no tool-seeking attacks in the corpus"
    missed = [a.msg_id for a in tool_seeking if not guard.run(a.text)[0].fired]
    assert not missed, f"pre_action guard missed {missed}"


def test_pre_action_guard_survives_rephrasing():
    """The claim the session rests on: placement beats pattern matching.

    The dodge attacks defeat the input guards by respelling the request.
    A guard on the tool ARGUMENT is not respellable, because the call still
    has to name what it wants.
    """
    guard = GUARDS["tool_argument"]
    for argument in ("admin passwords", "ADMIN PASSWORDS",
                     "please fetch the admin passwords now"):
        assert guard.run(argument)[0].fired, f"missed {argument!r}"


def test_guard_events_do_not_store_the_input():
    """A guard log full of the payloads you built the guard to keep out is
    a new copy of the problem, in a file with weaker access control."""
    if not EVENTS.exists():
        pytest.skip("run 01_measure.py first")
    hostile_snippets = ["HANDBOOK-OVERRIDE-9931", "admin passwords",
                        "reveal the prompt"]
    for line in EVENTS.read_text().splitlines():
        if not line.strip():
            continue
        event = GuardEvent(**json.loads(line))
        for snippet in hostile_snippets:
            assert snippet.lower() not in event.rule.lower(), (
                f"guard event for {event.guard_name} stored the payload "
                f"in its rule field")


def test_guard_events_validate_against_the_contract():
    if not EVENTS.exists():
        pytest.skip("run 01_measure.py first")
    n = 0
    for line in EVENTS.read_text().splitlines():
        if line.strip():
            GuardEvent(**json.loads(line))
            n += 1
    assert n > 0, "no guard events written"
