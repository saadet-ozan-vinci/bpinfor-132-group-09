# Week 11, the guardrails

Copy this into your project `DECISIONS.md`. In week 13 it becomes a section
of your report you do not have to write.

Every guard below needs BOTH numbers. A catch rate on its own is not a
result, because a guard that blocks everything has a perfect one.

## The guard table

| guard | placement | action | fail mode | caught | false blocks | us/call |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

The legitimate message your tighter guard blocks, quoted in full:

Whether you would ship that guard anyway, and the reasoning:

What the tightening bought, expressed as an exchange rate: how many extra
catches for how many blocked residents:

## Placement

For each guard, what it can DETECT and what it can PREVENT. These are
different columns and for at least one guard they differ:

| guard | detects | prevents |
|  |  |  |

The guard that survives rephrasing, and why placement rather than pattern
quality is the reason:

## What gets through

The attacks that pass every guard you built:

What they have in common with the attacks you do catch:

Why adding another pattern does not close this, in one sentence:

What would actually stop them, and what it would cost:

## Fail modes

| guard | fail mode | what happens to a legitimate request when it breaks | why you chose that |
|  |  |  |  |

The guard where you would choose differently if this were a payment system
rather than an information service:

## Layering

Does your stack catch more than your best single guard? If not, say so
plainly and say what the stack does buy:

Which guard you would delete if you had to cut latency, and what you would
lose:

## Logging

The evidence that your guard events store no payloads:

What a guard log would leak if you had recorded the input instead:

## Cost

Total added latency per request, all guards, in microseconds:

Whether that is affordable at your expected volume, with the arithmetic:

## What you are not defending against

One paragraph naming the attacks your stack cannot see at all. Week 12 will
red team exactly this list, so a thin answer here becomes a long afternoon
next week.
