"""The three agent setups used in the Week 5 comparison.

This is the week the hand-rolled loop of weeks 1 to 4 gives way to a
framework. Read the week 4 `agent.py` next to this file: the loop, the
message list, the tool dispatch, and the schema envelope are all gone. What
is left is the part that was always the design.

Nothing underneath has changed. Pydantic AI is making the same calls to the
same endpoint in the same wire format. That is why you wrote the loop first.

In beginner terms, this file sets up three ways of asking a language model
to fix the same bug:

* ``baseline`` can inspect files, edit one line, and run tests using tools.
* ``planner`` creates a structured plan; Python checks that plan.
* ``fixer`` proposes one structured line change. Python, not the model,
  applies that change.
* ``reviewer`` gives a separate approve/reject decision before the change is
  applied in architecture C.

Pydantic AI is the library that connects an ``Agent`` to the configured model
and handles requests, tool calls, and structured output. Pydantic is the
library that checks data against the Python models (``Plan``, ``Fix``, and
``Verdict``) declared below.
"""

from __future__ import annotations

import time  # Measures how long an agent proposal takes.
from typing import Literal  # Restricts the review decision to fixed choices.

from pydantic import BaseModel, Field  # Define and validate structured data.
from pydantic_ai import Agent, RunContext  # Create agents and access tool data.
# A fixer can exhaust its output retries when the model returns invalid data.
# Catch that specific Pydantic AI error so one bad attempt does not stop all runs.
from pydantic_ai.exceptions import UnexpectedModelBehavior

from repo import (  # Safe scratch-repository access and test/change helpers.
    Work, apply_fix, diff_summary, run_tests,
)

from project.models import LARGE, pydantic_ai_model  # Shared model configuration.

# Resolve the course project's configured model once, then pass it to each agent.
MODEL = pydantic_ai_model(LARGE)


# --------------------------------------------------------------------------
# TODO 1. The plan schema, and a warning about its shape.
# --------------------------------------------------------------------------

class Plan(BaseModel):
    """The shape of a planner response.

    ``BaseModel`` makes Pydantic check the model's response before this
    program uses it. The response must have text for ``goal``, a list of
    ``steps``, and a ``suspect_file``. ``Field`` adds instructions that are
    also supplied to the language model.
    """

    goal: str = Field(description="One sentence stating what needs to be fixed.")
    steps: list[str] = Field(description="A list of 2 to 6 step descriptions.")
    suspect_file: str = Field(description="The file name most likely containing the bug.")


PLANNER_SYSTEM_PROMPT = """You plan a small change to a Python repository. You have NO tools and you must not attempt to act: you are producing a plan that a person will read before anything runs.
Keep it to between two and six steps. Name the file you suspect.
One step MUST run tests. Never edit test files.

Examples:

User: Fix discount calculation where VIP members receive 0% discount instead of 15%.
Output:
{
  "goal": "Ensure VIP members receive the 15% discount.",
  "steps": [
    "Run tests to reproduce the failing VIP discount assertion.",
    "Inspect discounts.py logic handling VIP tier rates.",
    "Apply fix to the discount rate condition.",
    "Run tests again to verify the fix passes."
  ],
  "suspect_file": "discounts.py"
}

User: Booking total includes tax twice when extra baggage is selected.
Output:
{
  "goal": "Prevent baggage fees from triggering duplicate tax additions.",
  "steps": [
    "Run test suite to isolate the baggage fee calculation failure.",
    "Inspect pricing.py around tax aggregation.",
    "Fix duplicate tax calculation line.",
    "Re-run test suite to confirm."
  ],
  "suspect_file": "pricing.py"
}
"""

planner = Agent(
    MODEL,
    output_type=Plan,  # Ask Pydantic AI to parse/check the response as Plan.
    retries=5,  # Retry invalid structured responses; does not retry test failures.
    system_prompt=PLANNER_SYSTEM_PROMPT,  # Instructions sent with every planner request.
)

# --------------------------------------------------------------------------
# TODO 2. Validating the plan, for free, before anything runs.
# --------------------------------------------------------------------------

KNOWN_FILES = {"booking.py", "discounts.py", "pricing.py", "report.py"}


def validate_plan(plan: Plan) -> tuple[bool, list[str]]:
    """Check basic safety and usefulness rules using ordinary Python.

    Returns ``(is_valid, problems)``. A plan can be valid Pydantic data but
    still fail these checks: schema validation checks its shape, while this
    function checks our coursework rules and whether the named file exists.
    """
    problems: list[str] = []
    if not plan.goal.strip():
        problems.append("Plan goal must not be empty.")
    if not 2 <= len(plan.steps) <= 6:
        problems.append(
            f"Step count {len(plan.steps)} is outside the allowed range "
            "(expected 2 to 6)."
        )
    if any(not step.strip() for step in plan.steps):
        problems.append("Plan steps must not be empty.")
    if plan.suspect_file not in KNOWN_FILES:
        problems.append(
            f"Suspect file {plan.suspect_file!r} is not in the repository."
        )

    has_test_run = False
    for step in plan.steps:
        step_lower = step.casefold()
        mentions_tests = any(
            phrase in step_lower
            for phrase in ("test", "tests", "test suite", "run_tests")
        )
        proposes_test_edit = (
            mentions_tests
            and any(
                verb in step_lower
                for verb in (
                    "edit", "change", "modify", "update", "delete", "remove",
                )
            )
        )
        if proposes_test_edit:
            problems.append("Plan must not propose changing or removing tests.")
        if mentions_tests and any(
                verb in step_lower
                for verb in ("run", "execute", "rerun", "re-run")):
            has_test_run = True

    if not has_test_run:
        problems.append("Plan must include running the test suite.")
    return len(problems) == 0, problems


# --------------------------------------------------------------------------
# TODO 3. The fix, as a proposal rather than an edit.
# --------------------------------------------------------------------------

class Fix(BaseModel):
    """A request to replace exactly one source line.

    The model only proposes a change. ``apply_fix`` later verifies the path
    and exact old line before writing anything. The patterns reject newline
    characters so a response cannot accidentally ask to replace a whole
    function or file.
    """

    path: str = Field(
        description="Relative path to the source file to modify, e.g. discounts.py"
    )
    old_line: str = Field(
        min_length=1,
        max_length=300,
        pattern=r"^[^\r\n]+$",
        description=(
            "Exactly one physical source line to replace, copied "
            "character-for-character. Never include a whole function or "
            "newline."
        ),
    )
    new_line: str = Field(
        min_length=1,
        max_length=300,
        pattern=r"^[^\r\n]+$",
        description=(
            "Exactly one replacement source line, with no newline, function "
            "body, or surrounding explanation."
        ),
    )
    why: str = Field(
        max_length=160,
        description=(
            "A short plain-text reason. Do not include quotation marks or "
            "apostrophes."
        ),
    )


FIXER_SYSTEM_PROMPT = """You propose exactly ONE physical source-line replacement that fixes a failing test.
The old_line and new_line fields must each contain exactly one line with no newline characters. Never return an entire function, docstring, block, or file in either field. Copy old_line exactly as it appears on one line in the source. Keep why short and plain, without quotation marks or apostrophes.
Change the logic that is wrong. Do not change a constant to compensate for a wrong comparison, and never propose a change to a test.

Example:
Task: Fix off-by-one error where discount applies only when quantity > 10 instead of >= 10.
Output:
{
  "path": "discounts.py",
  "old_line": "    if quantity > 10:",
  "new_line": "    if quantity >= 10:",
  "why": "Change strict greater-than to greater-than-or-equal to match threshold specification."
}
"""

fixer = Agent(
    MODEL,
    output_type=Fix,  # Validate the proposed edit before returning it.
    retries=3,  # Keep the experiment's retry setting fixed at three.
    system_prompt=FIXER_SYSTEM_PROMPT,  # Explains the one-line response format.
)


# --------------------------------------------------------------------------
# The baseline, for comparison. Given complete: read it.
# --------------------------------------------------------------------------

class Work_(BaseModel):
    """An earlier illustrative dependency type; the active tools use ``Work``."""

    root_str: str
    model_config = {"frozen": True}


baseline = Agent(MODEL, system_prompt=(
    "You fix a bug in a small Python repository using the tools provided.\n"
    "run_tests to see the failure, read_file to look at the source, "
    "replace_line to change one line, run_tests again to confirm.\n"
    "Never edit anything under tests/. Stop as soon as the tests pass."))


@baseline.tool
def list_files(ctx: RunContext[Work]) -> list[str]:
    """Tool the baseline agent can call to discover Python source files.

    ``RunContext`` is Pydantic AI's way to pass trusted Python-side data
    (here, the scratch ``Work`` repository) to a tool function.
    """
    return ctx.deps.files()


@baseline.tool
def read_file(ctx: RunContext[Work], path: str) -> str:
    """Tool for reading a file using a path relative to the scratch root."""
    return ctx.deps.read(path)


@baseline.tool
def replace_line(ctx: RunContext[Work], path: str, old_line: str,
                 new_line: str) -> str:
    """Tool for requesting an exact one-line edit.

    The shared ``apply_fix`` function enforces the safety rules. The agent's
    instructions alone are not treated as a security boundary.
    """
    return apply_fix(ctx.deps, path, old_line, new_line)


@baseline.tool
def run_the_tests(ctx: RunContext[Work]) -> str:
    """Tool for running the deterministic tests and returning their output."""
    return run_tests(ctx.deps).output


# --------------------------------------------------------------------------
# TODO 5. The reviewer, which is the second agent.
# --------------------------------------------------------------------------

class Verdict(BaseModel):
    """The reviewer's structured decision and short explanation."""

    decision: Literal["approve", "reject"]
    reason: str = Field(max_length=200)


reviewer = Agent(
    MODEL,
    output_type=Verdict,  # Restrict the response to a checked Verdict.
    retries=3,  # Same fixed retry budget for each review.
    system_prompt=(
        "You have to review a diff against a failing test output and nothing else.\n"
        "Approve the change only if it fixes the bug's logic.\n"
        "Reject the change if it edits a test file or modifies a constant or does not solve the failure.\n"
        "Provide a short reason under 200 characters."
    ),
)


async def propose(work: Work, task: str, use_plan: bool) -> dict:
    """Run the planner (optionally) and ask for a single-line fix proposal.

    This function does not apply the proposal. It returns a dictionary of
    results for ``01_compare.py`` to review, apply, test, and record. The
    dictionary includes plan validation details, token use, timing, and—if
    the model repeatedly returns invalid structured output—a ``fix_error``.

    ``async`` lets Pydantic AI wait for model/network responses without
    blocking the Python event loop. ``await`` means "wait for this response
    before continuing".
    """
    out: dict = {"plan": None, "plan_ok": None, "plan_problems": [],
                 "fix": None, "applied": None, "tokens": 0}
    t0 = time.perf_counter()

    context = ""
    if use_plan:
        # ``planner.run`` sends the task to the model and validates the answer
        # as a Plan. ``r.output`` is the validated Plan, not raw response text.
        r = await planner.run(task)
        out["plan"] = r.output
        out["tokens"] += r.usage.total_tokens or 0
        ok, problems = validate_plan(r.output)
        out["plan_ok"], out["plan_problems"] = ok, problems
        print("Plan before any proposed change:")
        print(r.output.model_dump_json(indent=2))
        if ok:
            source_name = r.output.suspect_file
            context = (
                f"Follow this validated plan. Suspect file: {source_name}. "
                f"Goal: {r.output.goal}\n"
            )
        else:
            # Preserve the chosen experiment policy: warn, then use the known
            # source file rather than stopping this comparison run.
            source_name = "discounts.py"
            warnings = "\n".join(f"- {problem}" for problem in problems)
            print(
                "Plan validation warning; continuing with fallback "
                f"{source_name}:\n{warnings}"
            )
            context = (
                "The generated plan did not pass validation. Do not rely on "
                f"its suspect-file choice. Continue using the verified "
                f"fallback file {source_name}; make only a fix supported by "
                "the failing tests and the source.\n"
                f"Validation warnings:\n{warnings}\n"
            )
    else:
        source_name = "discounts.py"

    # Supply the fixer with real test output and source text so its proposal
    # is grounded in the current scratch copy.
    failing = run_tests(work).output
    source = work.read(source_name)
    prompt = (f"{context}File {source_name}:\n{source}\n\n"
              f"Failing test output:\n{failing}\n\n{task}")
    try:
        r = await fixer.run(prompt)
    except UnexpectedModelBehavior as exc:
        # Pydantic AI raises this after it cannot parse a valid Fix within
        # the configured retries. Return an explicit failed proposal so the
        # caller can record it and continue the remaining experiment runs.
        out["fix_error"] = (
            f"{type(exc).__name__}: the fixer did not produce a valid "
            f"one-line Fix after the configured retries ({exc})"
        )
        out["seconds"] = time.perf_counter() - t0
        return out
    # This is still only a proposal. The caller decides whether to ask the
    # reviewer and then calls ``apply_fix`` if the proposal is allowed.
    out["fix"] = r.output
    out["tokens"] += r.usage.total_tokens or 0
    out["seconds"] = time.perf_counter() - t0
    return out