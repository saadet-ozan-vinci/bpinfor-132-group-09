# Week 6: memory, a stateless MCP server, and an A2A channel

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 6

**Run conditions.** MCP SDK version: [ ] | specification revision:
2026-07-28 | model: [ ] | served locally | date: [YYYY-MM-DD]

### 1. The handle

Format I chose: opaque handle with uuid

A guessable handle would expose: a guessable handle would expose my backend making it vulnerable to unauthorized data access. 

### 2. Conflict and retention

- A write that contradicts an older fact: keep both, because you might need either depending on the context of the conversation.
- How long a record lives: 90, because it is a reasonable amount of time before the data becomes too stale.


### 3. What k costs

k = 3 . Tokens added per call: about 5 for the one returned fact in my lab demo (this is an estimation as there is no real llm call).
At four hundred facts in the store, this design scans and ranks the subject’s facts, then returns at most three matches.



### 4. Memory off against memory on

| | tokens | turns to finish |
| memory off | | |
| memory on | | |

[The interesting result is usually that memory costs more tokens per call
and fewer calls per task. Whether that is a win depends on the task, and
saying which way it went for you is the entry.]

### 5. The protocol, at the wire

| server mode | status | Mcp-Session-Id | answered |
| stateless_http=True | 200 | absent |  yes|
| stateless_http=False | 400 | ee7d76dcf96c4098b15c797378bbb8b0 | no |

The error the session-mode server returned, quoted exactly:

Bad Request: Missing session ID.

Why the two-server handle demonstration does not prove this on its own:

It just proves two servers can read the shared file. The same would work with a statefull protocol, so it doesn't prove the
protocol request is stateless.

### 6. What forget does not reach

[Deleting the fact does not un-say it: anything already copied into a
running conversation's messages is still there. Say what that means for a
resident who asks you to delete something.]

### Deferred

[Anything you did not get to, and why.]
