# Week 1: the stack, the first call, and what it costs

Copy this into your `DECISIONS.md` and fill it in. Keep the headings. In
week 13 this becomes a section of your project report that you do not have
to write.

---

## Week 1

**Run conditions.** Everything below was produced on:

- machine: Windows PC, Intel Core i7, 16 GB
- model: qwen3:4b-instruct
- served by: Ollama, one request at a time, locally
- date:  2026-09-16

Every number in this file is meaningless without those four lines, so they
are stated once here and referred to rather than repeated.

### 1. Machine and model set

I am running the  required plus optional model set.



### 2. The first call

| | |
| finish reason | |
| prompt tokens | |
| completion tokens | |
| elapsed | |

One sentence on the finish reason: what my program would do differently if
it came back as a truncation rather than a normal stop.

It could do one of the following: provide a hardcoded answer or change the prompt to force the model to answer with less 
tokens. (ex: Answer with 2 sentences)

### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
| closed_short, t=0.0 | 1/12 | 1/6| 0.29 s|
| closed_short, t=1.0 | 1/12 | 1/6| 0.31 s|
| open_list, t=0.0 | 1/12 |1/6 | 5.95 s|
| open_list, t=1.0 | 11/12 | 6/6| 4.88 s|

Which cell still returns a single answer at temperature 1.0, and why that
one: closed_short|t10 returns one distinct answer at temperature 1.0. Because the prompt asks
"What is the capital of Luxembourg? Answer in one word.", so the answer must be "Luxembourg" and nothing else. The
probability of getting "Luxembourg" is so high that even setting the temperature to 1.0 doesn't change the outcome. 

My machine does agree with the recording. 

Which cells a test asserting exact string equality would pass on, and what
that tells me about testing this system: closed_short|t00, closed_short|t10, open_list|t00 pass.
The string equality assertion is just a character by character check. It cannot verify if the meaning of those answers 
were the same or not.




**The sentence that carries into week 10.** You can rely on repeating an output when the prompt has an obvious answer,
like a one word fact. Otherwise, the output might be different everytime so we cannot rely on it. 

### 4. The cold start

- cold call: [10.86 ] s
- warm call: [0.74 ] s
- ratio: [14.73 ]

What this implies for a system that uses more than one model, and what I
will do about it:

On a machine with limited RAM, it is best to not go back and forth between models. For fast answers, use one model only.
Because the machine will need to unload and load the models each time it does a switch, meaning it will take much longer
to give an answer. 

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
| small tier | 0.03| 3.28|
| large tier |2.49 | 244.14|

Estimates against the price list dated [date in `project/prices.py`], not
measurements. Running locally, my actual monetary cost was zero.

Which tier I would run nightly, which I would run before a release, and why
not the same one for both:

I'd run the small tier nightly and run the large tier before a release.
Running large tier every night would be too expensive but it is good to run it before a release to really test our application. 

### Deferred

[Anything you did not get to, and why. An explicit deferral with a reason is
engineering. Silence is not, and the project rubric can tell the
difference.]
