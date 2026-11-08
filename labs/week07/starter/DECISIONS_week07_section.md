# Week 7: a RAG pipeline you can score

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 7

**Run conditions.** embedding model: nomic-embed-text:latest | dimensionality: 768 | chunk size:
600 | overlap: 80 | k: 5 | store: Chroma | date: 2026-11-07] | table from:
my own index

### 1. The chunker

size 600 lexical tokens, overlap 80 lexical tokens, because bigger chunks mean better section context and the overlap can
carry information across chunk boundaries making everything more flexible without being too large.

### 2. The index

56 chunks, 768 dimensions, 11.02 seconds for one full indexing run.

### 3. The table

| qid |   dense rank | keyword rank | recall@5 | tags                   |
|-----|-------------:|-------------:|---------:|------------------------|
| Q01 |            1 |            4 |     1.00 | distractor, superseded |
| Q02 |            1 |            4 |     1.00 | rare-token             |
| Q03 |            1 |            2 |     1.00 | easy                   |
| Q04 |            1 |            1 |     1.00 | vocabulary             |
| Q05 |           17 |           11 |     0.00 | multi-document         |
| Q06 |            1 |            1 |     1.00 | negation               |
| Q07 |            1 |            2 |     1.00 | easy                   |
| Q08 |            1 |            1 |     1.00 | numeric                |
| Q09 |            1 |            4 |     1.00 | distractor             |
| Q10 |            1 |            1 |     1.00 | easy                   |
| Q11 |            1 |           13 |     1.00 | easy                   |
| Q12 | unanswerable |            — |        — | unanswerable           |

### 4. Good pipeline, or easy task?

[Ten of eleven questions rank the gold chunk first. Say which of the two
that is evidence for. One sentence, and be honest.]

### 5. The question that fails on both

Question: Q05, Dense rank 17, keyword rank 13.

Why it fails: This question combines two different infromation needs, but the retrieval treats them as one single.
That means no gold section matches this query exactly, and the retrieval strugglest to find a good match.

Would any chunk size fix it? No, because the problem here is about the query itself, and not about the chunks. It would be 
a good idea to divide the query into two and try to answer each one separately. That would mean the retrieval would be mor accurate.

### 6. The gold-set correction

The note said: [ ]

My measurement said: [ ]

The corrected note:

[...]

[What it cost you to find this: one measurement. What it would have cost to
not find it: a stretch exercise built on a false premise, and a term in
which nobody noticed.]

### Deferred

[Anything you did not get to, and why.]
