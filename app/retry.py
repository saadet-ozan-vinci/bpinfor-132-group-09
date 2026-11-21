"""Stage: retries, fallback, and the degrade path. Replaced in week 8.

Until you wire yours in, there is no policy: every step is called exactly
once, nothing is retried, no fallback is tried, and an exception propagates.
That is the week 8 baseline, the run you recorded before fixing anything.

To replace it, copy your `labs/week08/starter/retry.py` and `faults.py`
into `app/`, then change the sibling import in `retry.py`:

    from faults import ContractDrift, RateLimited, ServerError, ToolTimeout
    from .faults import ContractDrift, RateLimited, ServerError, ToolTimeout

Keep these names and signatures, because `pipeline.py` calls them:

    StepPolicy, Attempt, StepResult
    is_retryable(exc) -> bool
    call_with_policy(fn, *args, policy, fallback=None, validate=None,
                     **kwargs) -> StepResult

The policies themselves live in `pipeline.py`, one per step, because the
lecture's rule is to choose them per step, in advance, by consequence.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from .faults import ContractDrift, RateLimited, ServerError, ToolTimeout


@dataclass
class StepPolicy:
    attempts: int = 3
    base_delay: float = 0.05
    jitter: bool = True
    max_elapsed: float = 5.0
    on_exhausted: str = "degrade"       # or "escalate"


@dataclass
class Attempt:
    n: int
    error: str | None
    slept: float = 0.0


@dataclass
class StepResult:
    value: object = None
    ok: bool = False
    attempts: list[Attempt] = field(default_factory=list)
    used_fallback: bool = False
    outcome: str = "ok"                 # ok | fallback | degraded | escalated

    @property
    def tries(self) -> int:
        return len(self.attempts)


def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (ToolTimeout, RateLimited, ServerError))


def call_with_policy(fn, *args, policy: StepPolicy, fallback=None,
                     validate=None, **kwargs) -> StepResult:
    result = StepResult()
    started = time.monotonic()
    attempts = max(1, policy.attempts)

    for number in range(1, attempts + 1):
        try:
            value = fn(*args, **kwargs)
            if validate is not None:
                validate(value)
            result.value = value
            result.ok = True
            result.outcome = "ok"
            result.attempts.append(Attempt(number, None))
            return result
        except Exception as exc:
            result.attempts.append(Attempt(number, str(exc)))
            if not is_retryable(exc) or number >= attempts:
                break

            elapsed = time.monotonic() - started
            remaining = policy.max_elapsed - elapsed
            if remaining <= 0:
                break

            maximum_delay = policy.base_delay * (2 ** (number - 1))
            delay = (random.uniform(0, maximum_delay)
                     if policy.jitter else maximum_delay)
            delay = min(delay, remaining)
            if delay > 0:
                time.sleep(delay)
                result.attempts[-1].slept = delay
            if time.monotonic() - started >= policy.max_elapsed:
                break

    if fallback is not None:
        try:
            result.value = fallback(*args, **kwargs)
            result.ok = True
            result.used_fallback = True
            result.outcome = "fallback"
            return result
        except Exception as exc:
            result.attempts.append(Attempt(result.tries + 1, str(exc)))

    result.ok = False
    result.outcome = ("degraded" if policy.on_exhausted == "degrade"
                      else "escalated")
    return result
