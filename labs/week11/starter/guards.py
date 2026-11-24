"""Guards, their placements, and what happens when a guard itself breaks.

Three things are declared for every guard and none of them is optional:

  placement   pre_model, post_model, or pre_action. WHERE it runs decides
              what it is able to prevent, which is a different question
              from what it is able to detect.
  action      allow, flag, block, or rewrite. What happens on a match.
  fail_mode   open or closed. What happens when the GUARD throws, which is
              the case nobody writes down and everybody eventually meets.

The last one is the reason `GuardEvent` has a `fail_mode_triggered` field.
A guard that crashes has not made a decision, and something still has to.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable, Literal

Placement = Literal["pre_model", "post_model", "pre_action"]
Action = Literal["allow", "flag", "block", "rewrite"]
FailMode = Literal["open", "closed"]

INJECTION_MARKER = "HANDBOOK-OVERRIDE-9931"

# Names that a tool call must never carry. Least privilege expressed as
# data rather than as a sentence in a prompt, which is the week 4 lesson.
# Mapped to a CATEGORY, never logged as the matched string. A guard log
# that records what it blocked is a fresh copy of the payload, in a file
# with weaker access control than the system you were protecting.
FORBIDDEN_TOOL_ARGS = {
    "admin passwords": "credential-seeking",
    "system prompt": "prompt-extraction",
    "credentials": "credential-seeking",
}


@dataclass
class Verdict:
    fired: bool
    rule: str = ""
    rewritten: str | None = None
    errored: bool = False


@dataclass
class Guard:
    name: str
    placement: Placement
    action: Action
    fail_mode: FailMode
    fn: Callable[[str], Verdict]

    def run(self, text: str) -> tuple[Verdict, float, bool]:
        """Return (verdict, milliseconds, fail_mode_triggered).

        A guard that raises does NOT propagate. It is a control, and a
        control that takes the request down with it has converted a
        detection problem into an availability problem. What it does
        instead is declared, per guard, in `fail_mode`.
        """
        t0 = time.perf_counter()
        try:
            verdict = self.fn(text)
            triggered = False
        except NotImplementedError:
            # Deliberately NOT swallowed. An unwritten guard is a bug in
            # your code, not a fault in production, and turning it into a
            # fail-closed verdict would hide the TODO behind a table of
            # plausible-looking blocks.
            raise
        except Exception as exc:                      # noqa: BLE001
            # fail closed: treat the request as hostile, because an
            # unavailable control is not the same as a passed one.
            # fail open: let it through, and say so loudly in the event.
            verdict = Verdict(fired=(self.fail_mode == "closed"),
                              rule=f"guard errored: {type(exc).__name__}",
                              errored=True)
            triggered = True
        return verdict, (time.perf_counter() - t0) * 1000.0, triggered


# --------------------------------------------------------------------------
# TODO 1, answered. Two input guards, and the difference between them is
# the whole trade-off of the session.
# --------------------------------------------------------------------------

# TODO 1a. Four or five patterns for the obvious phrasings. Start here,
# measure, and resist the urge to make them clever yet.
NAIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bignore\s+(my|your)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bforget\s+(my|your)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(my|your)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bignore\s+(my|your)\s+last\s+email\b", re.IGNORECASE),
    re.compile(r"\bi\s+am\s+the\s+administrator\b", re.IGNORECASE),
]
# TODO 1b. Tighter: require an imperative verb AND an object meaning
# "the thing you were told before", so that "ignore my last email"
# survives and "ignore your instructions" does not.
#
# One warning that has already cost this lab a catch. `\binstruction\b`
# does NOT match "instructions", because the character after the word
# is a word character and the boundary fails. Write the plurals.
# Nothing will report an error; you will simply catch less.
TIGHTER_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(ignore|forget|disregard)\s+my\s+(last|previous|prior)\s+(instruction|instructions|message|email|request)s?\b", re.IGNORECASE),
    re.compile(r"\b(ignore|forget|disregard)\s+(the|those)\s+(last|previous|prior)\s+(instruction|instructions|message|email|request)s?\b", re.IGNORECASE),
]


def _match(patterns: list[str]) -> Callable[[str], Verdict]:
    """Given. Returns the first matching pattern as the rule."""
    def run(text: str) -> Verdict:
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return Verdict(True, pattern)
        return Verdict(False)
    return run


def redact_marker(text: str) -> Verdict:
    """TODO 2. post_model, action=rewrite.

    Fire when INJECTION_MARKER appears in the model's output, and put a
    redacted copy in `Verdict.rewritten`.

    Before you write it, answer this in one line in DECISIONS.md: what can
    this guard actually PREVENT? It runs after the model has been called
    and after any tool has run, so the honest answer is nothing. It
    contains, it does not defend, and knowing the difference is the point
    of declaring a placement at all.
    """
    if INJECTION_MARKER not in text:
        return Verdict(False)

    return Verdict(
        fired=True,
        rule="injection marker detected",
        rewritten=text.replace(INJECTION_MARKER, "[REDACTED]"),
    )


def forbidden_tool_argument(argument: str) -> Verdict:
    """TODO 3. pre_action, action=block. The only guard here that prevents.

    Fire when the argument of a tool call contains a forbidden term, and
    report the CATEGORY rather than the matched string. A guard log that
    records what it blocked is a fresh copy of the payload in a file with
    weaker access control, and there is a gate in test_guardrails.py that
    fails if you get this wrong.

    This guard runs on a tool argument rather than on prose, which is why
    the dodge attacks in the corpus do not defeat it. Placement, not
    cleverness.
    """
    raise NotImplementedError("TODO 3: forbidden_tool_argument")


GUARDS: dict[str, Guard] = {
    "input_naive": Guard("input_naive", "pre_model", "block", "closed",
                         _match(NAIVE_PATTERNS)),
    "input_tighter": Guard("input_tighter", "pre_model", "block", "closed",
                           _match(TIGHTER_PATTERNS)),
    "output_marker": Guard("output_marker", "post_model", "rewrite", "closed",
                           redact_marker),
    "tool_argument": Guard("tool_argument", "pre_action", "block", "closed",
                           forbidden_tool_argument),
}
