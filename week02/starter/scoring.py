"""The scorer. Two TODO markers, and it is the most important file today.

A prompt change is not an improvement until it has been measured, and this
is what measures it. Write it before you tune anything, because a scorer
written after you have seen the output tends to score what the output
already does.

One rule, and it decides most of the marks in this session: report per
field, as counts. Never one overall accuracy. Ten records means one error
moves a percentage by ten points, and an average across four fields hides
the only interesting thing in the data, which is that they do not move
together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from unicodedata import category

from week02.starter.documents import Gold

FIELDS = ("category", "urgency", "due_date", "quote")


@dataclass
class FieldResult:
    correct: bool
    got: object
    expected: object
    note: str = ""


@dataclass
class Scoreboard:
    """Counts per field, plus the failures worth reading."""

    hits: dict[str, int] = field(
        default_factory=lambda: {f: 0 for f in FIELDS})
    total: int = 0
    invalid: int = 0
    failures: list[tuple[str, str, str]] = field(default_factory=list)

    def as_counts(self) -> str:
        return "  ".join(f"{f} {self.hits[f]:>2}/{self.total}"
                         for f in FIELDS)


# --------------------------------------------------------------------------
# TODO 3. Score one record against its gold annotation.
# --------------------------------------------------------------------------

def score_one(record, gold, document_text: str) -> dict[str, FieldResult]:
    """Compare one extracted record with its gold annotation, per field.

    Three of the four fields compare in the obvious way. One does not.

    category and urgency are closed label sets, so equality is the whole
        test and a wrong answer is detectable with no model involved. That
        is why the task was designed with closed label sets.

    due_date needs care. The gold is either an ISO date string or None.
        Decide now what you do about `""`, about `"null"` as a string, and
        about a correctly formatted date that is simply the wrong date. Two
        of those three are the same kind of wrong and one is not, and your
        DECISIONS.md should say which convention you chose.

    quote is the interesting one and it is free. The record is correct only
        if the string the model returned appears verbatim inside
        `document_text`. Use `in`. Do not lowercase, do not strip
        punctuation, do not "be reasonable about whitespace". The moment you
        relax this check you have stopped measuring whether the model copied
        and started measuring whether it approximately copied, and the whole
        value of the field was that it was exact.

    Return a dict keyed by field name.
    """
    #check category
    category_correct = record.category == gold.category
    category_res = FieldResult(correct=category_correct, got=record.category, expected=gold.category)

    #check urgency
    urgency_correct = record.urgency == gold.urgency
    urgency_res = FieldResult(correct=urgency_correct,got=record.urgency, expected=gold.urgency)

    #check due date
    date_iso = record.due_date.isoformat() if record.due_date else None
    due_correct = (date_iso == gold.due_date)
    due_res = FieldResult(
        correct=due_correct,
        got=date_iso,
        expected=gold.due_date,
    )

    #check quote
    quote_correct = bool(record.quote and record.quote in document_text)
    quote_res = FieldResult(correct=quote_correct, got=record.quote, expected="substring of document_text")

    return {"category": category_res, "urgency": urgency_res, "due_date": due_res, "quote": quote_res}

# --------------------------------------------------------------------------
# TODO 4. Aggregate.
# --------------------------------------------------------------------------

def score_all(records, golds, docs) -> Scoreboard:
    """Roll the per record results into per field counts.

    `records` is a list of (ServiceRequest or None). A None means validation
    failed, and it must be counted: increment `invalid`, and count every
    field as wrong for that document. A scorer that silently skips the
    records it could not parse reports a number that improves every time the
    model gets worse, which is the most dangerous kind of metric.

    Append the interesting failures to `failures` as
    (doc_id, field, one line of what went wrong), because at the checkpoint
    you will be asked which records failed and why, not what your average
    was.
    """
    fields = ["category", "urgency", "due_date", "quote"]
    hits = {"category": 0, "urgency": 0, "due_date": 0, "quote": 0} #the amount of times each field was correct
    total = 0 #nb of total documents
    invalid= 0 #nb of invalid documents
    failures = [] #failed fields

    for i in range(len(records)):
        record = records[i]
        document = docs[i]
        gold = golds[document.id]
        total = total + 1
        if record is None:
            invalid += 1
            for field in ["category", "urgency", "due_date", "quote"]:
                failures.append((document.id, field, "validation failed: record is None"))
        else:
            score = score_one(record, gold, document.text)
            for field in fields:
                res = score[field]
                if res.correct:
                    hits[field] += 1
                else:
                    reason = res.note or f"got {res.got!r}, expected {res.expected!r}"
                    failures.append((document.id, field, f"{field} failed: {reason}"))

    return  Scoreboard(hits, total, invalid, failures)

# --------------------------------------------------------------------------
# Given.
# --------------------------------------------------------------------------

def compare(a: Scoreboard, b: Scoreboard, label_a: str, label_b: str) -> str:
    """Two scoreboards side by side, per field, with the movement."""
    lines = [f"{'field':<10} {label_a:>12} {label_b:>12} {'move':>7}"]
    lines.append("-" * 44)
    for f in FIELDS:
        move = b.hits[f] - a.hits[f]
        lines.append(f"{f:<10} {a.hits[f]:>9}/{a.total} {b.hits[f]:>9}/{b.total} "
                     f"{move:>+7d}")
    lines.append(f"{'invalid':<10} {a.invalid:>12} {b.invalid:>12}")
    return "\n".join(lines)
