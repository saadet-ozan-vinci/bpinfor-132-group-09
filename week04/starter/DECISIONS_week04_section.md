# Week 4: a ReAct loop with two tools

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 4

**Run conditions.** agent model: qwen2.5:7b | temperature: 0.0 | step cap: 6 |
budget: none (managed through step cap) | stall limit: 2 | served locally | date: 2026-10-13 |
scored on: my own machine

### 1. The two tool descriptions

| tool | what its "do not use this for" clause prevents |
| search_services | Prevents the model from looking up arithmetic expressions, translation or personal reference. |
| compute | Prevents passing units, currency symbols or any language into the tool and prevents the model from doing the math itself |

### 2. The three caps

| cap | value | why that value |
| steps | 6 | If we go even lower, most our requests will not be completed in the limited count, if we go higher it will take too long and be expensive |
| budget | none | Because the token budget is undirectly bounded by step count and context_budget.  |
| no progress | 2 | Allows one retry but terminates on the second no progress to avoid a loop |

My definition of progress is accessing new document IDs that were not previously seen in the session, and it does **not** fire when there is only one stall..

### 3. Task accuracy

4/10 passed. Failed: 'T-01', 'T-03', 'T-04', 'T-05', 'T-07', 'T-09'.

Steps: min 1, max 2, mean 1.6. Caps fired: 0.

### 4. What the tools bought

No-tool baseline: 1/10. With tools: 4/10.

One sentence on what the tools bought, and at what cost per task:

[...]

### 5. The four findings

| finding | result |
| tool abuse on T-08 | |
| invention on T-10 | |
| refusal with zero tool calls | |
| notice board: text reached the model | |
| notice board: agent followed it | |

[Quote the invented answer if there was one. An invented figure with an
invented citation is worse than one without, and it is worth having the exact
words in front of you when you write entry 6.]

### 6. Blast radius

Prompt-level defenses tried: [ ] of 8 blocked the injection.

Given that an attacker **can** make this agent say anything, the worst thing
they can make it **do** is:

[...]

That answer depends on the fact that this agent's only tools are a read-only
search and a calculator. It changes the moment the agent gains a tool that
writes, sends, or pays, because [ ].

What I would build first to bound that, and the week I expect to build it in:

[...]

[Week 12 will ask you to find this entry. Writing down a vulnerability you
have found and not yet fixed, with the week you expect to fix it, is exactly
what a security backlog is.]

### Deferred

[Anything you did not get to, and why.]
