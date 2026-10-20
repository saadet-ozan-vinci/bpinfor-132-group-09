"""The three agents, on Pydantic AI. TODO 1 to 5.

This is the week the hand-rolled loop of weeks 1 to 4 gives way to a
framework. Read the week 4 `agent.py` next to this file: the loop, the
message list, the tool dispatch, and the schema envelope are all gone. What
is left is the part that was always the design.

Nothing underneath has changed. Pydantic AI is making the same calls to the
same endpoint in the same wire format. That is why you wrote the loop first.
"""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from repo import Work, apply_fix, diff_summary, run_tests

from project.models import LARGE, pydantic_ai_model

MODEL = pydantic_ai_model(LARGE)


# --------------------------------------------------------------------------
# TODO 1. The plan schema, and a warning about its shape.
# --------------------------------------------------------------------------

class Plan(BaseModel):
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
    output_type=Plan,
    retries=5,
    system_prompt=PLANNER_SYSTEM_PROMPT,
)

# --------------------------------------------------------------------------
# TODO 2. Validating the plan, for free, before anything runs.
# --------------------------------------------------------------------------

KNOWN_FILES = {"booking.py", "discounts.py", "pricing.py", "report.py"}


def validate_plan(plan: Plan) -> tuple[bool, list[str]]:
    problems = []

    # Check step count
    if not (2 <= len(plan.steps) <= 6):
        problems.append(f"Step count {len(plan.steps)} is outside of the allowed range. (expected: between 2 and 6)")

    # Check existence of suspect file
    if plan.suspect_file not in KNOWN_FILES:
        problems.append(f"Suspect file {plan.suspect_file} is not in known files.")

    # Check if plan runs tests and does not propose editing them
    has_test_step = False
    for step in plan.steps:
        step_lower = step.lower()
        if "test" in step_lower:
            if any(verb in step_lower for verb in ("edit", "change", "modify", "update")):
                problems.append("Plan cannot propose editing a test file.")
            else:
                has_test_step = True

    if not has_test_step:
        problems.append("Plan doesn't include running tests")

    return len(problems) == 0, problems


# --------------------------------------------------------------------------
# TODO 3. The fix, as a proposal rather than an edit.
# --------------------------------------------------------------------------

class Fix(BaseModel):
    path: str = Field(description="Relative path to the file to modify, e.g. discounts.py")
    old_line: str = Field(description="Exact single line to replace, copied character for character.")
    new_line: str = Field(description="The replacement line.")
    why: str = Field(description="Short reason for the fix.")


FIXER_SYSTEM_PROMPT = """You propose exactly ONE line change that makes a failing test pass.
You are given the whole file. Return the single wrong line, copied character for character, and the corrected version of it.
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
    output_type=Fix,
    retries=3,
    system_prompt=FIXER_SYSTEM_PROMPT,
)


# --------------------------------------------------------------------------
# The baseline, for comparison. Given complete: read it.
# --------------------------------------------------------------------------

class Work_(BaseModel):
    root_str: str
    model_config = {"frozen": True}


baseline = Agent(MODEL, system_prompt=(
    "You fix a bug in a small Python repository using the tools provided.\n"
    "run_tests to see the failure, read_file to look at the source, "
    "replace_line to change one line, run_tests again to confirm.\n"
    "Never edit anything under tests/. Stop as soon as the tests pass."))


@baseline.tool
def list_files(ctx: RunContext[Work]) -> list[str]:
    """List the Python files in the repository."""
    return ctx.deps.files()


@baseline.tool
def read_file(ctx: RunContext[Work], path: str) -> str:
    """Read one file, by a path relative to the repository root."""
    return ctx.deps.read(path)


@baseline.tool
def replace_line(ctx: RunContext[Work], path: str, old_line: str,
                 new_line: str) -> str:
    """Replace one exact line. The old line must appear exactly once."""
    return apply_fix(ctx.deps, path, old_line, new_line)


@baseline.tool
def run_the_tests(ctx: RunContext[Work]) -> str:
    """Run the test suite and return its output."""
    return run_tests(ctx.deps).output


# --------------------------------------------------------------------------
# TODO 5. The reviewer, which is the second agent.
# --------------------------------------------------------------------------

class Verdict(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(max_length=200)


reviewer = Agent(
    MODEL,
    output_type=Verdict,
    retries=3,
    system_prompt=(
        "You have to review a diff against a failing test output and nothing else.\n"
        "Approve the change only if it fixes the bug's logic.\n"
        "Reject the change if it edits a test file or modifies a constant or does not solve the failure.\n"
        "Provide a short reason under 200 characters."
    ),
)


async def propose(work: Work, task: str, use_plan: bool) -> dict:
    """One attempt: optionally plan, then propose a fix, then verify."""
    out: dict = {"plan": None, "plan_ok": None, "plan_problems": [],
                 "fix": None, "applied": None, "tokens": 0}
    t0 = time.perf_counter()

    context = ""
    if use_plan:
        r = await planner.run(task)
        out["plan"] = r.output
        out["tokens"] += r.usage.total_tokens or 0
        ok, problems = validate_plan(r.output)
        out["plan_ok"], out["plan_problems"] = ok, problems
        context = (f"A plan has already been made. Suspect file: "
                   f"{r.output.suspect_file}. Goal: {r.output.goal}\n")
        source_name = (r.output.suspect_file if r.output.suspect_file
                                                in KNOWN_FILES else "discounts.py")
    else:
        source_name = "discounts.py"

    failing = run_tests(work).output
    source = work.read(source_name)
    prompt = (f"{context}File {source_name}:\n{source}\n\n"
              f"Failing test output:\n{failing}\n\n{task}")
    r = await fixer.run(prompt)
    out["fix"] = r.output
    out["tokens"] += r.usage.total_tokens or 0
    out["seconds"] = time.perf_counter() - t0
    return out