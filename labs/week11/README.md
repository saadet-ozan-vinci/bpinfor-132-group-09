# Week 11 practical: guardrails that fail safe

BPINFOR-132, Designing, Verifying, and Shipping AI Agents.
Duration: 2 teaching units, 90 minutes. Bring a laptop and your project.

## Where this fits

Week 10 built the harness that measures whether your system works. This week
adds the controls that bound what happens when it does not, and measures
those the same way.

The target is week 4's injection, which is the honest choice because week 4
already told you how that goes. Four prompt-level defenses were tried there, on two models,
and none of them blocked the attack. Today you build guards in code instead,
and find out exactly how much better that is, which is more than nothing and
much less than a solution.

Everything today is offline. The guards are code, the traffic is fixed, and
the whole matrix reproduces exactly on any machine. There is no model call in
this session at all, which is deliberate: a control you cannot reproduce is
not a control.

## Why this session exists

Because catch rate is the wrong number on its own, and it is the only number
most people report.

A guard that blocks every message has a catch rate of 100 percent. The
number that makes catch rate mean anything is what the same guard does to
people who came to ask a question. On the reference corpus, tightening the
input guard raises catches from 4 to 7 out of 9 and blocks one real
resident, G-04, who wrote "Ignore the previous email I sent, I found the
answer myself." That exchange rate is the only thing worth arguing about, and
you cannot argue about it if you never measured the second half.

## Learning outcomes exercised

Outcome 9 (designing and implementing layered guardrails, including input
validation, output validation, and policy enforcement at the boundary),
outcome 8 (interpreting results and distinguishing detection from
prevention), outcome 12 (justifying trade-offs in cost, latency, reliability,
and safety), and outcome 3 (bounding failure severity, the safety dimension
of AAR-Rabanser). This is the eleventh increment of the project deliverable.

## Timing

| Time | Block | What you do |
| 0 to 8 | Set up | Read both corpora, especially the twelve legitimate messages |
| 8 to 40 | Guards | TODO 1, 2, 3, then `01_measure.py` |
| 40 to 65 | Layers and fail modes | `02_layers.py`, and the attacks nothing catches |
| 65 to 85 | Gates | TODO 4, then `pytest` |
| 85 to 90 | Close | Commit, push, and write `DECISIONS.md` |

## What you build

| File | Marker | What it is |
| `guards.py` | TODO 1a, 1b | two input guards, naive and tighter |
| `guards.py` | TODO 2 | an output guard that rewrites |
| `guards.py` | TODO 3 | a pre-action guard on a tool argument |
| `test_guardrails.py` | TODO 4a, 4b | the two gates about false blocks |

Every guard declares three things and none is optional: **placement**
(pre_model, post_model, pre_action), **action** (allow, flag, block,
rewrite), and **fail_mode** (open or closed).

## The four things this session insists on

**Measure both corpora, always.** `traffic.py` has twelve legitimate messages
and nine attacks. Several of the legitimate ones sit deliberately close to
the trigger words, because real users say "ignore my last message" and "can
you override my appointment" constantly. A guard tuned only against attacks
has never met them.

**Placement decides what a guard can PREVENT, which is not what it can
detect.** The output guard fires after the model has been called and after
any tool has run. It can keep evidence out of a reply. It cannot stop
anything. The pre-action guard catches fewer attacks and is the only one that
prevents, because of where it sits.

**Patterns are a spelling test.** Two attacks in the corpus pass every guard
you will build: one inserts a space ("I gnore"), one is in German. They say
exactly what the caught ones say. You cannot close that gap by adding
patterns, because the attacker writes the next one after seeing which one you
added. What survives rephrasing is the guard on the tool argument, since the
call still has to name what it wants.

**Declare the fail mode.** A guard that raises has not made a decision, and
something still has to. Fail closed and a broken guard takes your service
down for everyone. Fail open and a broken guard is indistinguishable from a
guard that approved. Neither is right in general, so choose per guard and
write it down. What is not optional is the record: every `GuardEvent` carries
`fail_mode_triggered`, so "the guard passed it" and "the guard was not
working" are two different rows.

## A warning about your logs

A guard log that stores what it blocked is a fresh copy of the payload, in a
file with weaker access control than the system you were protecting. The
`rule` field records WHICH RULE matched, never the input. There is a gate
that fails if you get this wrong, and it caught exactly this mistake in the
reference solution while it was being written.

## What to expect, so you do not misread it

Layering will not raise your catch rate on this corpus. The tighter input
guard alone catches everything the whole stack catches, and a gate demanding
otherwise would fail and would be right to. What the stack buys is that the
best catcher is also the only one with a false block, so you cannot get both
properties from one guard. Say that plainly rather than pretending the layers
are independent.

## Homework

Add one attack of your own that defeats every guard you built, and one
legitimate message that your guards wrongly block. Both go in `traffic.py`
with a note. A corpus that only contains attacks somebody else wrote is a
corpus you cannot be surprised by, and week 12 is going to try to surprise
you.
