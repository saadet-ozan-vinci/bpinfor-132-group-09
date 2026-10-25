# Week 5 practical: a planner, an executor, and a second agent

BPINFOR-132, Designing, Verifying, and Shipping AI Agents.
Duration: 2 teaching units, 90 minutes. Bring a laptop.

## What your system gains this week

Increment five, and two changes at once.

The hand-rolled loop from week 4 gives way to **Pydantic AI**. Open your
week 4 `agent.py` next to this week's `agents.py`: the loop, the message
list, the tool dispatch, and the schema envelope are all gone. Nothing
underneath has changed, the framework makes the same calls to the same
endpoint in the same wire format, which is exactly why you wrote the loop
first.

And the agent gains a **planner** and a **reviewer**, so there are three
architectures to compare rather than one to admire.

## Why this session exists

The lecture put every multi-agent pattern on one axis, who decides the
control flow, and argued that a second agent is only worth it for tool
coordination or genuinely distinct expertise. Today you test that on your own
task, with a cost number attached, against a verifier that cannot be argued
with.

Coding is the domain for one reason: it is the only agentic task in this
course with a free, fast, deterministic verifier. The tests pass or they do
not. Every other domain has to build a judge, and that is weeks 10 to 12.

## Learning outcomes exercised

Outcome 2 (patterns and their trade-offs), outcome 6 (decomposing a problem
into an architecture), outcome 12 (justifying trade-offs).

## Before you arrive

Read ADP-Gulli chapters 6 and 7, and MAS-Dibia chapter 1 on when **not** to
use multi-agent. Install the one new dependency:

```bash
pip install "pydantic-ai-slim[openai]"
```

## Timing

| Time | Block | What you do |
| 0 to 10 | Setup | Install, run the test suite, read the failure and the four modules |
| 10 to 45 | Plan and fix | TODO 1 to 4: the plan schema, its validator, and the fix proposal |
| 45 to 70 | Second agent | TODO 5: the reviewer, and the three-way comparison |
| 70 to 85 | Measure | TODO 6 and 7: read the table, and the gold set |
| 85 to 90 | Close | Commit, push, write the numbers into `DECISIONS.md` |

## The task and the toy repository

A small booking-fee library for a commune sports hall: four modules, sixteen
tests, no dependencies. One test fails. The off-peak discount is meant to
apply from 20:00, and a booking starting at exactly 20:00 misses it.

The agent works on a **copy**. `Work.fresh()` makes one per run, so a
destructive agent costs you nothing. If you edit `toyrepo/` directly, your
next run starts from a repository that is already fixed and every number
after that is meaningless.

## The three architectures

| | what it can do |
| A baseline | free-form tool loop: list, read, replace any line, run tests |
| B planner | plan, validate the plan for free, then propose **one** line change |
| C planner + reviewer | the same, with a second agent gating the proposal |

One variable changes across them: how much architecture sits between the
model and the edit.

## A beginner's guide to the code

The code for the three agents is in `starter/agents.py`; the experiment
runner is `starter/01_compare.py`; and the copied project, test runner, and
safe line-edit function are in `starter/repo.py`.

### A few library words in plain English

**Pydantic** checks that data has the shape your Python code expects. For
example, a planner response must have a goal, a list of steps, and a file
name. `BaseModel` declares that shape, and `Field` adds constraints or
instructions to individual fields.

**Pydantic AI** connects a model to your program. An `Agent` holds the model,
instructions, and expected response type. Calling `await agent.run(...)`
sends a request and waits for the response. If the expected response type is
set, Pydantic AI checks that response before returning it.

A **tool** is a Python function the model is allowed to request. In
architecture A, the baseline agent can list files, read a file, request a
line replacement, and run tests. Python runs each tool; the model does not
directly reach into the file system.

`RunContext[Work]` gives a tool access to the Python-side `Work` object for
the current temporary repository copy. `async` and `await` are Python's way
of waiting for a model response without blocking the whole asynchronous
program.

### How one planned attempt works

1. `Work.fresh()` copies the toy repository into a new temporary directory.
   Each attempt gets its own copy so an earlier fix cannot affect later
   measurements.
2. In architectures B and C, the planner returns a `Plan`. Pydantic checks
   the response shape; `validate_plan` then applies additional rules such as
   whether the file is known and the plan includes running tests.
3. If the plan fails those rules, this experiment prints the problems and
   follows its chosen fallback policy: it continues with `discounts.py`.
   This is a policy choice for the experiment, not a feature supplied by
   Pydantic.
4. The fixer receives the selected source file, the failing test output, and
   the task. It returns a `Fix` proposal containing the file, the exact old
   line, the replacement line, and a short reason. The fixer does not write
   the change itself.
5. In architecture C, a separate reviewer receives the proposed diff and
   failing test output and returns `approve` or `reject`. A rejection blocks
   the edit.
6. `apply_fix` checks the path and old line before editing the temporary
   copy. It refuses test files, paths outside the copy, missing files,
   missing lines, and ambiguous lines. These checks are performed by Python;
   they do not depend on the model following its instructions.
7. The test suite runs on the resulting copy. That test result, not the
   planner's confidence or the reviewer's approval, determines whether the
   row is green.
8. The attempt's measurements are saved, and its temporary copy is removed.

### Understanding the model response types

The `Plan`, `Fix`, and `Verdict` classes in `agents.py` inherit from
Pydantic's `BaseModel`. Think of them as forms with named fields:

| Type | Fields | Purpose |
| --- | --- | --- |
| `Plan` | `goal`, `steps`, `suspect_file` | A proposed sequence of work |
| `Fix` | `path`, `old_line`, `new_line`, `why` | One proposed source-line replacement |
| `Verdict` | `decision`, `reason` | The reviewer's approval or rejection |

For example, `Literal["approve", "reject"]` means the decision must be one of
those two exact strings. The `Fix` line fields also disallow newline
characters: this keeps a one-line proposal from accidentally becoming a
whole function or file. These checks can reject malformed answers, but they
cannot prove that a syntactically valid answer is a correct fix. The tests
and the edit guard provide separate checks.

The `UnexpectedModelBehavior` import in `agents.py` is used to catch one
specific failure: Pydantic AI could not get a valid structured `Fix` from
the model within the existing retry limit. The program records that as a
failed proposal so the remaining experiment attempts can continue. This
does not change the retry count or turn the failed response into a
successful fix.

### Reading the comparison

`--runs 3` runs each architecture three times. The model may give different
answers on different attempts, so the results are evidence from a small
experiment rather than a guarantee about all tasks or models.

* **green** means the toy repository's test suite passed after that attempt.
* **tokens** is the model usage reported by Pydantic AI; more agent steps
  usually mean more model work.
* **seconds** is elapsed time for the attempt.
* **reviewer=approve** only means the reviewer approved the proposal. The
  edit can still be refused by `apply_fix`, and the tests can still fail.
* A plan warning is recorded separately. Under this experiment's policy, an
  invalid plan falls back to the known `discounts.py` file rather than
  stopping the attempt.

The program writes detailed rows to
`artifacts/week05_architectures.json` and records trace entries separately.
Always distinguish results from your own live run from the supplied replay
recording. Use the live measurements and your own reasoning when completing
your decisions document.

## Block 1, plan and fix (35 minutes)

TODO 1 to 4 in `agents.py`.

**TODO 1 carries a warning worth reading before you write it.** The obvious
plan schema is a list of nested `Step` objects. It does not work on this
model, and it does not fail gracefully: it raises
`Exceeded maximum output retries` every time. A flat list of strings
validates. Schema complexity is a cost you pay in reliability, and the right
schema is the shallowest one that carries what you need.

**TODO 3 is the design decision of the session.** The executor does not edit
the file. It proposes exactly one line change, and `repo.apply_fix` decides
whether to apply it, refusing anything that touches a test, names a line that
is not there, or is ambiguous. Note who enforces that: not the model, and not
its instructions.

**Checkpoint 1.** The six items in `checklist.md`.

## Block 2, the second agent (25 minutes)

TODO 5. The reviewer sees the diff and the test output, and **not** the
fixer's reasoning. If it inherits the reasoning it inherits the mistake, and
the second opinion stops being a second opinion.

Then run all three architectures and read the table.

**Checkpoint 2.** Be ready to say which architecture you would ship and what
the other two cost.

## Working with the recording

```bash
python starter/01_compare.py --replay
```

Week 5's recording is different from weeks 1 to 4. Those record model calls
and replay them. This one records the **outcome** of each whole pipeline,
three times per architecture, because the pipeline mutates a copy of a
repository and replaying calls into a changing file system would be a lie.

The baseline in the recording is slow and never succeeds. That is the
finding, not a defect.

## What goes into DECISIONS.md today

Six entries. Template in `starter/DECISIONS_week05_section.md`.

1. Your plan schema, and what happened when you tried a nested one.
2. Your validator: which checks, and what happens when one fails.
3. The three-way table: green out of three, tokens, and seconds each.
4. One sentence on **why** the baseline fails, that is not "the model is too
   small".
5. The reviewer's verdict on each run, and whether you would ship it.
6. What your verifier cannot catch. This is the most valuable line on the
   page and week 10 comes back for it.

## Homework

- Run all three live, three times each, and put your table next to the
  recorded one.
- Task B, the refactoring: the same discount rates are written out in four
  places and should become one. It has no single failing test to guide it,
  so the planner matters far more. Report whether the gap between
  architectures widens.
- `python -m project.verify` passing, gold set at 46 cases.

## If you finish early

- Hand the reviewer a deliberately bad patch: one that deletes the failing
  test instead of fixing the bug. `apply_fix` refuses it, so hand the
  reviewer the diff directly. Does it catch it? A reviewer that approves it
  has told you something the happy path never would.
- Make the fixer propose the wrong-but-passing fix on purpose, by telling it
  the constant is suspect. Then check whether your reviewer catches it and
  whether the test suite does. One of them should.

## Reference solution

In `solution/`, published after the session. The written answer to TODO 6 is
at the bottom of `01_compare.py`, and the second and third points in it are
the ones worth reading.
