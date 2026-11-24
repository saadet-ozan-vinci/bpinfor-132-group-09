# Guardrail design worksheet

BPINFOR-132, week 11. One page. Fill it in before you write code, finish
it when you have measurements, and paste it into `DECISIONS.md` at the
end of the session. It is a graded deliverable and it is a section of the
project report you will not have to write in week 13.

Print it, or keep it open in a second window. Do not do this from memory.

---

## Part 1, before you write anything (minute 0 to 8)

One row per guard. Four columns, and none of them is optional.

| # | Guard | Placement | Cost guess | Fail mode | Worst case if it stops firing |
|---|-------|-----------|-----------|-----------|-------------------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Placement** is one of four, and they are not interchangeable.

- `input`, before the model call, so before you have paid for one
- `contract`, on the reply, as a type. Free, fast, exactly right.
- `output`, after the contract and before the user
- `action`, before the world changes. The only layer where a failure is
  not recoverable by apologising.

**Cost guess** in milliseconds and in money. Guess now, in ink. You
replace it with a measurement in part 2, and being wrong by a factor of
ten about the cost of your own check is common and worth noticing.

**Fail mode** is what happens when the guard itself errors, times out, or
cannot reach its dependency. Not what happens when the rule matches.

- `closed`: the request does not proceed. Correct when the guarded
  outcome is severe or irreversible. Turns an outage of your safety
  dependency into an outage of your product.
- `open`: the request continues and the failure is recorded. Correct when
  the guard is advisory, noisy, or bounds a low-severity outcome. Needs
  an alert on the failure rate, otherwise it degrades into having no
  guard at all.

The fail mode follows the **outcome being guarded**, not the guard's
implementation. The same classifier can be fail closed on a path that
issues payments and fail open on a path that answers opening hours.

**Worst case** is one sentence, written as a person rather than as a
rate: what reaches the user or the world if this guard silently stops
firing. If that sentence is unacceptable, one guard was never enough and
you need a second layer at a different placement. That is what layered
means.

---

## Part 2, when you have numbers (minute 40 to 65)

| Guard | Fires on attacks | Blocks | False positives | Advisory noise | Added p95 | Cost guess was |
|-------|------------------|--------|-----------------|----------------|-----------|----------------|
| | / 9 | | / 12 | | ms | too high / too low / about right |
| | / 9 | | / 12 | | ms | |
| | / 9 | | / 12 | | ms | |
| | / 9 | | / 12 | | ms | |
| | / 9 | | / 12 | | ms | |

- **Fires** means the rule matched. An advisory guard fires without
  blocking, and it still has to be observed firing, otherwise you cannot
  tell a working detector from one that always returns allow.
- **Blocks** means the request stopped.
- **False positives** are legitimate requests that were blocked. Never
  report a block rate without this column. Block rate on its own is a
  number you can make perfect by blocking everything.
- **Advisory noise** is a guard firing on a legitimate request without
  blocking it. Nobody was refused, so it is not a false positive, but it
  is what you would inherit if you ever made that guard blocking.
- **Added p95**, not the mean. Guards are serial with the model call, so
  their cost is additive and it lands on the tail.

Run conditions for every number above, stated once:

- Date:
- Mode (offline stub or online) and model:
- Input sets and their sizes:
- Machine and concurrency:

---

## Part 3, the ship decision (one sentence per guard)

| Guard | Ship as | Because |
|-------|---------|---------|
| | blocking / advisory / high-severity paths only / not at all | |
| | | |
| | | |
| | | |
| | | |

The rows will not all say the same thing, and a table where they do is a
table where somebody stopped thinking. A free and exact guard is always
on. A cheap and partial guard ships with an acknowledged gap. A noisy
guard ships advisory. An accurate and slow guard is routed to the paths
where the outcome justifies the latency.

---

## Part 4, the two questions

**Have you seen it fire?**

| Guard | Fired in a test | Fired by hand | Record inspected |
|-------|-----------------|---------------|------------------|
| | yes / no | yes / no | yes / no |
| | | | |
| | | | |
| | | | |
| | | | |

A guardrail you have never seen fire is a guardrail you do not have.
There are three explanations for a guard that never fires and you cannot
tell them apart from production traffic: it is broken, it is not on the
request path, or nobody has attacked it yet. Only a test separates them.

**What is it for, honestly?**

For each guard, one line: what does this bound **on its own**, with every
other guard removed. Guards that turn out to bound nothing on their own
are not useless, they are advisory, and they should be declared as such
rather than trusted as controls.

| Guard | Bounds on its own | Depends on which other layer |
|-------|-------------------|------------------------------|
| | | |
| | | |
| | | |
| | | |
| | | |

---

## Part 5, for week 12

- The guard I least trust, and why:
- The escaped case I have not fixed, and what I would do about it:
- The layer that is currently doing more work than it can carry:
