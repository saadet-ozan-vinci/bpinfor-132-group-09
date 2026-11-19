# Week 10, the evaluation harness

Copy this into your project `DECISIONS.md` and fill it in. In week 13 this
becomes a section of your report you do not have to write.

This is the first week whose numbers are ABOUT your other weeks, so every
figure needs to say which runs it covers and when they were recorded.

## Conditions

- Traces covered: how many, from which weeks, recorded when: 916 traces; weeks 1, 2, 3, 4, 5, 6; recorded from 2026-09-16 
to 2026-11-09
- Judge model and version: qwen3:4b-instruct through ollama 0.6.3
- Judge threshold: 0.5
- Harness versions (deepeval, ragas, pytest):DeepEval 4.3.4, RAGAS 0.4.4, pytest 9.1.1
- Run date: 2026-11-19

## The free layer

| week | runs | accuracy | consistency | robustness | predictability | safety |
| 5 | 34 | 0.47 | 0.22 | n/a | 1.00 | 0.00 |
| 8 |  0| n/a | n/a | n/a | n/a | n/a | 
| 9 |  0| n/a | n/a | n/a | n/a | n/a |
| app | 19 | 0.58 | 1.00 | 1.00 | 0.00 | 1.00 |
| all |  916| 0.91 | 0.84 | 0.97 | 0.22 | 0.72 |

Note: week 8 and 9 have no runs because they were not implemented in time for this run. So i need to rerun this after 
implementing to be able to answer the following questions.

Which week has the best accuracy, and what do its other columns say: 

Which week has the best predictability, and what does its accuracy say:

In one sentence: what ranking these systems by accuracy alone would have
told you, and why it would have been wrong:

### The n/a cells

List every dimension that returned None, and for each one say whether it is
an ABSENCE (you have no evidence yet) or a DEFECT (you could have had
evidence and your instrumentation threw it away).

Week 8 and 9 returned n/a for all dimensions because they were not implemented yet.
| week | dimension | absence or defect | what would fix it |


The case ids in weeks 5 and 8 encode something they should not. Say what,
and what it cost you:

## The labels

The label you disagreed with, and your reasoning:

Whether you changed the label or kept it, and why:

## The judge

Agreement with the hand labels at your chosen threshold:

| | human pass | human fail |
| judge pass | 5 | 0 |
| judge fail | 0 | 7 |

The threshold sweep:

| threshold | agreement | false pass | false fail |
| 0.15 | 0.50 | 6 | 0 |
| 0.25 | 0.67 | 4 | 0 |
| 0.35 | 0.75 | 3 | 0 |
| 0.45 | 1.00 | 0 | 0 |
| 0.50 | 1.00 | 0 | 0 |
| 0.55 | 1.00 | 0 | 0 |
| 0.65 | 0.92 | 0 | 1 |
| 0.75 | 0.83 | 0 | 2 |
| 0.85 | 0.83 | 0 | 2 |


The band where agreement is perfect: 0.45 to 0.55

Where your threshold sits inside that band, and who chose it: the middle of the perfect agreement band.

Which of false pass and false fail is worse for YOUR system, in one sentence
that names the consequence rather than the metric: A false pass is worse because it could provide false information as 
if it's true and mislead people as if it were true.

## Cost

| layer | model calls | wall clock | can it run on every commit |
| deterministic checks | 0 |  microseconds to seconds | yes |
| the four dimensions | 0 | microseconds to seconds | yes |
| the judge | 12 | 49s | no |

Pre-commit: deterministic conditions 
CI: no judge tests (pytest or ragas)
Before release: test with everything judge included.

## The gates

| gate | what it protects | what a failure would mean |
| Traces exist |An evaluation has input |The build can run with no evidence |
| Trace conditions exist | Measurements are comparable | Results lack model or run-date conditions |
| Predictability ≥ 50% | Failures signal themselves | A large share of failures can be silent |
| Judge agreement ≥ 80% | The judge matches humans | Its scores are unsuitable for gating |
|  No false passes | Invented answers cannot receive a pass | The gate may approve unsafe answers |
| Threshold cliff ≤ 10% change | The threshold is not fragile | Agreement depends on an arbitrary cutoff |

For each gate, how you made it fail on purpose: 
Set the threshold to 0.15 and observed agreement drop to 50% with six false passes.

Any gate that asserts a number from this week rather than a property that
should hold for any healthy version, and why you kept it anyway:
none of the gates assert a number from this week rather than a property that should hold for any healthy version.

## What you will not claim

The harness doesn't prove correctness for unseen questions or identify all system output problems. The judge only measures
agreement against 12 human written cases. If we had a bigger sample of human written cases, we would be able to identify
more failures and do better monitoring.
