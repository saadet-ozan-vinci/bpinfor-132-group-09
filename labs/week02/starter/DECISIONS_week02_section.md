# Week 2: a structured-output extractor, measured

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 2

**Run conditions.** model: qwen3:4b-instruct | temperature: 0.0 | prompt version: [ ] |
served locally | date: [2026-09-27] | scored on: my own
machine

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: None type. If a ticket doesn't mention a name the model assumes it doesn't
exist so not to hallucinate. 
- due_date, when the message states only a relative expression: It puts a None type. It would be hard to attempt it to turn it into an actual ISO date, making it prone to error.
- quote, and what "verbatim" means in my scorer: It means the original document text that is provided contains the quote extracted by the model.
- what my scorer does with a record that failed validation: It increments the invalid count and scores 0 hits on all fields for that record.

If the scorer skips the unparsable records, it would affect the actual performance evaluation by increasing the percentage of success when the output gets worse.

### 2. Zero-shot, per field

| field | correct | of |
| category | 7 | 10 |
| urgency | 6 | 10 |
| due_date | 5 | 10 |
| quote | 3 | 10 |
| invalid records | 0 | 10 |

My prediction, written before block 3: examples will help most on category and urgency
because those are predefined closed labels, the more examples you give the better the model will understand how to classify.
The other fields are more open-ended.

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
| EX-01 | Shows non-blocking issue gets standard for urgency and demonstrates a None date when no date is mentioned. An example for the access category.| urgency, due_date, category |
| EX-03 | German example showing how to treat German text. Demonstrates date parsing with slashes into ISO. An example for the hardware category.| category,  due_date |
| EX-04| Demonstrates that relative date mentions still need to be None. Demonstrates the use of info urgency and other category.| due_date, category, urgency |
| EX-05|French example showing how to treat French text. Demonstrates parsing written dates into ISO. An example for the billing category.  |due_date, category |

| field | zero-shot | few-shot | move |
| category | 7/10 | 5/10 | -2 |
| urgency | 6/10 | 9/10 | +3 |
| due_date | 5/10 | 8/10 | +3 |
| quote | 3/10 | 7/10 | +4 |

### 4. What got worse

The category field got worse, going from 7/10 in zero-shot to 5/10 in few-shot.
It could be because we didn't give examples for each category. So it might have chosen the categories in the examples more often.


[Name the field, if any, and diagnose it. If nothing got worse, say so and
say how you checked. Then look at the failure lines rather than the counts,
and say whether any error disappeared or merely changed shape. A wrong label
that became a different wrong label has not been fixed.]

### 5. What the examples cost

- extra input tokens per call: 329
- per thousand calls: 329000
- estimated euros per thousand calls on the small tier: 0.20, against the
  price list dated 2026-08-10. Estimate, not a measurement.

### 6. Ship it or not

[Which variant, on what evidence, and what would change your mind. Ten
records is not enough to be confident and saying so is worth more than
claiming a win. If your answer is "keep one example and drop the rest", say
which one and why.]
I would not ship the four-example few-shot variant. While it improved performance on the three following fields, quote (+4),
urgency (+3), and due_date (+3), it regressed on the category field dropping to 5/10. That accuracy is too low for
the application to function to user satisfaction. The model clearly needs better prompting for all categories,
ideally with at least one example for each. Furthermore, ten records is not a enough of a sample size to make a good
shipping decision. 
### Sensitivity variant

Variant assigned: role. What I changed: I added single sentence, telling what the role is to the prompt. What moved: 
Accuracy shifted for some fields: category (+2) and due_date(+1) improved, quote (-1) dropped and urgency(+0) was unchanged.
French documents had fewer errors (5 to 3).

[If nothing moved, say so. A knob that changes nothing measurable is a real
result, and it tells the room which knobs are worth arguing about.]

### The gold set

Ten cases written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect: It cannot detect if the quote chosen by the model is relevant or not.
The only check is that the quote is a substring of the original document_text.

[This is the most valuable line on the page. An example: "our scorer cannot
tell a correctly formatted date that is simply the wrong date from a
correctly extracted one, because it only compares strings."]

### Deferred

[Anything you did not get to, and why.]
