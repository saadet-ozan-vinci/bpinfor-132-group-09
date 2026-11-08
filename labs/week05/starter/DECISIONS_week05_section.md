# Week 5: a planner, an executor, and a second agent

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 5

**Run conditions.** model: ollama:qwen2.5:7b | framework: Pydantic AI v2.57.0 |
runs per architecture: 3 | served locally | date: 2026-10-20 |
table from: my own runs

### 1. The plan schema

What I tried first, and what happened:

    The planner initially produced unreliable or malformed structured output that failed schema parsing due to inconsistent 
    formatting from the model.

What I shipped, and why it is shaped that way:

    I shipped a flat plan schema (list[str]) backed by few-shot prompting. The few-shot examples ground the model's syntax
    and constrain the output format directly, avoiding parsing failures without adding complex schema validation layers

### 2. The validator

| check | what it catches |
| step count range (2 to 6)| Too short plans or runway loops with too many steps|
|suspected file validation | Hallucinated file paths not present in the repository  |
| verification step presence | Plans that propose edits without mentioning a test or verification step|

On a failed check my system logs validation result and falls back to the safe default, because it won't stop the execution 
when the plan is mostly right and requires less tokens that reparing.

### 3. The three-way table

| architecture | green | tokens (mean) | seconds (mean) |
| A baseline | 2/3 |19817 |269.1 |
| B planner | 3/3 | 1763 |52.8 |
| C planner + reviewer |1 /3 | 2521|61.3 |

### 4. Why the baseline fails

[Not "the model is too small". Look at what changed between A and B: it is
not the model and it is not the prompt. Name it.]

### 5. The reviewer

Verdicts across my runs: [ ] approve, [ ] reject.

Would I ship it: [ ]. Extra cost: [ ] tokens, [ ] seconds per run.

The case where it would earn its cost:

[...]

### 6. What my verifier cannot catch

[The most valuable line on this page. The test suite is free, fast, and
deterministic, and it still only checks the cases somebody wrote a test for.
Name a change that would make the suite green and still be wrong. Week 10
comes back for this.]

### Deferred

[Anything you did not get to, and why.]
