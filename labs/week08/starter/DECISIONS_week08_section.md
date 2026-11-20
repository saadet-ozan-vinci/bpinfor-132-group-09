# Week 8: retries, recovery, and a human approval gate

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 8

**Run conditions.** fault seed: 42 | attempts: 3 | base delay: 0.02 |
max elapsed: 3.0 | LangGraph 1.2.22 | date: 2026-11-20

### 1. Which errors are retryable

Retryable: timeout, rate limit, and server error. Flaky server errors are also
retryable because the fault is transient.

Deliberately NOT retryable: contract drift, because the call succeeded and the
response is valid but does not match the expected contract.

Retrying a successful call with contract drift is worse than useless because it
repeats the same valid but incompatible response instead of fixing the contract.

[The one that matters is contract drift. Say in one sentence why retrying a
call that succeeded is worse than useless.]

### 2. The fault matrix

| | correct | WRONG | degraded | failed |
| baseline | 1 | 0 | 2 | 5 |
| hardened | 2 | 0 | 5 | 1 |

What hardening actually bought: Reduced failures from 5 to 1 and converted those failures into degraded answers that can
identify the missing information. It also increased correct answers from 1 to 2. No confident wrong answers were produced.


### 3. The empty result

An empty result is not an error. My pipeline treats it as a degraded answer, because the tool managed to respond but didn't
provide any supporting information.

### 4. The gate

Gated step: submit. The others are not gated because  they are reversible preparation steps, while submission has an external
and potentially irreversible consequence.

An unanswered approval after the timeout: reject. That protects the system and
the user from an unattended submission..

The approval payload carries exact submission arguments and supporting evidence and deliberately does not carry model-generated approval text.

### 5. The duplicate the state does not show

I put a side effect above the interrupt. It executed 2 times. The recorded
state showed it 1 time.

What that means for anything my gated node does before it asks:
Anything before interrupt() must be read-only or idempotent. External side
effects such as sending emails, writing records, or submitting payments must
happen only after approval.


### Deferred

Nothing.
