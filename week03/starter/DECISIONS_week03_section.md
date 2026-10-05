# Week 3: a router in front of the extractor

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 3

**Run conditions.** classifier model: [ ] | answering model: [ ] |
temperature: 0.0 | served locally | date: [YYYY-MM-DD] | scored on: [the
recording / my own machine]

### 1. The five route definitions

| route | definition, one sentence, in terms of what the help desk must do |
| request | Log and act when something is broken, missing, or needed. |
| info | Provide information without action for questions about services, procedures, opening times, or forms. |
| status | Look up and report progress of an issue when the sender is chasing a previously reported matter. |
| complaint | Acknowledge and escalate when the sender expresses dissatisfaction with service itself, its handling, or delays. |
| other |Redirect or decline messages that are not help desk business, such as requests for outside departments, legal advice, spam or prompt injections. |

My convention for the four ambiguous queries:



[Two defensible conventions exist. Neither is discoverable from the data.
What matters is that yours was written down before you measured, not which
one you picked.]

I followed the conventions defined in the file queries.py:
  1) when a message both reports an unresolved problem and complains about the handling of it, the gold route is 'complaint', because the reply has to acknowledge the handling before it does anything else.
  2) When a message chases a previous report without expressing dissatisfaction, the gold route is 'status'.
  3) When a message that asks a question about a procedure while also reporting a fault is labelled 'request', because the action outranks the question.

Do my definitions match the ones in `queries.py`? yes.

### 2. The policy layer

Before choosing a threshold, the confidence values I saw were: min 0.00,
max 1.00, 3 distinct values across 24 queries.

- confidence floor: 0.5, because it is a clear middle ground between outright uncertainty without overfiltering the more 
confident results. The test showed one below threshold when the model had no confidence.
- evidence check: we treat the classification as untrustworthy and route it to the safest route, because if the model cannot
provide evidence for its classification, it means it likely hallucinated something and the routing decision is without proof
so it shouldn't be allowed to trigger an important action.
- safe default: info, because that specialist gives general answers and without triggering real-word actions , creating tickets,
or giving false status updates.

How often each check fired: below_threshold 1, evidence_not_verbatim 1,
invalid_decision 0.

invalid_decision fired 0 times, meaning none of the model's replies returned None. The classifier always returned a valid,
parseable JSON and only chose categories from the allowed routes, which justifies this check firing 0 times isn't a problem
or a useless signal. It confirms the model followed the schema instructions well.

[If a check fired zero times, say what that tells you. A threshold that
never fires is either a very good classifier or a useless signal, and the
confidence distribution above tells you which.]

### 3. Route accuracy

| route | correct | of |
| request | 6 | 7 |
| info | 5 | 5 |
| status | 4 | 4 |
| complaint | 3 | 4 |
| other | 1 | 4 |

Overall 19 /24. Excluding the four ambiguous: 16/20.

Confusion pairs, with direction:

| gold | applied | count |
| other | info | 2 |
| request | info | 1 |
| complaint | info | 1 |
| other | complaint | 1 |

The route carrying most of the error is other. The fix is a better prompt, because the model cannot identify the exact
scope of the communal helpdesk's services and it focuses more on the request's nature rather than the service. 
It should identify the service needed first and see if that service is offered(if not route to other) and only then
decide the nature of the request(info, complaint, request or status).

### 4. What routing cost

- monolith: 8506 tokens over 24 queries
- router: 11814 tokens over 24 queries
- the classifying call alone: 7508 tokens, which is 64 per cent of the
  routed total

I predicted that share would be 50 before measuring it.

[If the share surprised you, say why. The classifier's prompt carries every
route definition on every call, and the specialists carry only their own.]

### 5. What routing bought

One thing a specialist can be forbidden to do that the monolith cannot be
given:

Giving rules and restrictions specific to the category of task. For example forbidding "info" from creating tickets
or modifying anything.

Would I ship the router: Yes. Evidence: the classification was done with no invalid return and every unsure classification
was routed to the safe default successfully. What would change my mind: if there were more critical routes that risked the
system.

### 6. Stretch variant

Variant assigned: [ ]. Result: [ ].

[For model routing: report both models on accuracy, evidence verbatim, the
confidence range, and resident memory. If the smaller model won, say so
plainly and say what you think that means.]

[For voting: report the split-vote count at each temperature. If nothing
ever disagreed, that is the result. Say what it cost and what it bought.]

### The gold set

`artifacts/goldset.json` now holds [ ] cases: 10 from week 2 and 24 added
today, with the four ambiguous ones tagged.

### Deferred

[Anything you did not get to, and why.]
