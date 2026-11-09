"""The memory store, and the handle.

Two things live here and they are easy to confuse.

**Memory** is what the agent remembers about a resident across runs: facts,
written once and searched later. It is a store.

**A handle** is a name for a piece of state that the agent carries in its own
messages. It is not memory, it is an address. `open_case` mints one, and
every later call passes it back as an ordinary argument.

The distinction is the whole week. Block 2 shows why: when the protocol stops
carrying state for you, the state does not vanish, it becomes an argument
with a name the model can see.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

DEFAULT_PATH = Path("artifacts/memory_store.json")
RETENTION_PERIOD = timedelta(days=90)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass
class Fact:
    subject: str
    kind: str
    text: str
    handle: str
    written_at: str
    expires_at: str


@dataclass
class MemoryStore:
    """A file-backed store. Deliberately not a database and not a vector store.

    Week 7 replaces `search` with real retrieval over embeddings. Keep the
    keyword version behind this one method and next week costs you ten lines
    instead of a refactor.
    """

    path: Path = DEFAULT_PATH
    facts: list[Fact] = field(default_factory=list)
    cases: dict[str, dict[str, object]] = field(default_factory=dict)

    # ----------------------------------------------------------------
    # Writing, and the handle it returns.
    # ----------------------------------------------------------------

    def write(self, subject: str, kind: str, text: str) -> str:
        """Append one fact and return a handle for it.

        Three decisions here, and all three go in DECISIONS.md with a reason.

        What does a handle look like? A sequential `fact-0007` tells anyone
        who sees it how many facts exist and lets them guess `fact-0006`,
        which is a read of somebody else's data. Week 12 attacks exactly
        this.

        What happens when a new fact contradicts an older one? Keeping both
        means `recall` can return two contradictory facts and something has
        to cope. Overwriting means losing what changed and when. Pick one.

        Records expire 90 days after creation. Expired entries are removed
        when the store is loaded, so no background cleanup process is needed.
        """
        now = _utcnow()
        handle = f"fact-{uuid4()}"
        self.facts.append(Fact(
            subject=subject,
            kind=kind,
            text=text,
            handle=handle,
            written_at=_timestamp(now),
            expires_at=_timestamp(now + RETENTION_PERIOD),
        ))
        self.save()
        return handle

    # ----------------------------------------------------------------
    # Searching, and what k costs.
    # ----------------------------------------------------------------

    def search(self, subject: str, query: str, k: int = 3) -> list[str]:
        """Return at most k remembered facts about ONE subject.

        Scope to the subject BEFORE you score anything. That is not an
        optimization, it is the boundary that stops one resident's memory
        leaking into another's conversation, and it belongs here rather than
        in a sentence asking the model not to do it.

        Keyword overlap is fine. Week 7 replaces the body of this method
        with embeddings and the signature does not change, so keep the
        matching inside this one method.

        Then answer, at the checkpoint: what does k cost you in tokens per
        call, and what happens when the store holds four hundred facts?
        """
        if isinstance(k, bool) or not isinstance(k, int) or k < 0:
            raise ValueError("k must be a non-negative integer")
        if k == 0:
            return []

        # Scope before scoring: facts for other subjects never enter ranking.
        subject_facts = [fact for fact in self.facts
                         if fact.subject == subject]
        query_terms = set(re.findall(r"\w+", query.casefold()))
        if not query_terms:
            return []

        scored = []
        for fact in subject_facts:
            fact_terms = set(re.findall(
                r"\w+", f"{fact.kind} {fact.text}".casefold()))
            score = len(query_terms & fact_terms)
            if score:
                scored.append((score, fact.text))
        scored.sort(key=lambda result: result[0], reverse=True)
        return [text for _, text in scored[:k]]

    # ----------------------------------------------------------------
    # Forgetting, which is not optional.
    # ----------------------------------------------------------------

    def forget(self, handle: str) -> bool:
        """Hard delete by handle. Return whether it existed.

        Not optional. A store that can only be written to is not a store you
        can operate, and "we keep everything forever" is an answer with a
        legal department attached to it.

        One line in DECISIONS.md about what this does NOT reach: anything
        already copied into a running conversation's messages. Deleting the
        fact does not un-say it.
        """
        remaining = [fact for fact in self.facts if fact.handle != handle]
        if len(remaining) == len(self.facts):
            return False
        self.facts = remaining
        self.save()
        return True

    # ----------------------------------------------------------------
    # The handle, which is block 2's subject
    # ----------------------------------------------------------------

    def open_case(self, subject: str) -> str:
        """Mint an explicit handle for a piece of ongoing state."""
        now = _utcnow()
        handle = f"case-{uuid4()}"
        self.cases[handle] = {
            "subject": subject,
            "expires_at": _timestamp(now + RETENTION_PERIOD),
        }
        self.save()
        return handle

    def subject_of(self, handle: str) -> str | None:
        case = self.cases.get(handle)
        if case is None:
            return None
        subject = case.get("subject")
        return subject if isinstance(subject, str) else None

    # ----------------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------------

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "facts": [vars(f) for f in self.facts],
            "cases": self.cases,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "MemoryStore":
        store = cls(path=path)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            now = _utcnow()
            changed = False

            for record in data.get("facts", []):
                record = dict(record)
                if "expires_at" not in record:
                    written_at = _parse_timestamp(record["written_at"])
                    record["expires_at"] = _timestamp(
                        written_at + RETENTION_PERIOD)
                    changed = True
                fact = Fact(**record)
                if _parse_timestamp(fact.expires_at) > now:
                    store.facts.append(fact)
                else:
                    changed = True

            for handle, value in data.get("cases", {}).items():
                if isinstance(value, str):
                    # Legacy cases had no creation time; start retention at migration.
                    case = {
                        "subject": value,
                        "expires_at": _timestamp(now + RETENTION_PERIOD),
                    }
                    changed = True
                else:
                    case = dict(value)
                    if "expires_at" not in case:
                        case["expires_at"] = _timestamp(now + RETENTION_PERIOD)
                        changed = True
                if _parse_timestamp(case["expires_at"]) > now:
                    store.cases[handle] = case
                else:
                    changed = True
            if changed:
                store.save()
        return store
