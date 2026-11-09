"""Persistent personal memory and the Week 7 knowledge-base retriever.

The application has two kinds of retrieval. `search` is the stable pipeline
entry point for commune-corpus retrieval; Week 7 replaced its body with the
dense index. `search_memory` retrieves facts remembered about one subject and
is used by the MCP `recall` tool. Keeping these paths separate preserves the
Week 7 pipeline while preventing one subject's memories from leaking to
another.
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
    """A file-backed personal-memory store and a Week 7 corpus retriever."""

    path: Path = DEFAULT_PATH
    facts: list[Fact] = field(default_factory=list)
    cases: dict[str, dict[str, object]] = field(default_factory=dict)

    def write(self, subject: str, kind: str, text: str) -> str:
        """Append a fact with an opaque UUID handle and 90-day retention."""
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

    def search_memory(self, subject: str, query: str,
                      k: int = 3) -> list[str]:
        """Return at most k keyword matches scoped to one subject."""
        if isinstance(k, bool) or not isinstance(k, int) or k < 0:
            raise ValueError("k must be a non-negative integer")
        if k == 0:
            return []

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

    def search(self, subject: str, query: str, k: int = 3) -> list[str]:
        """Retrieve commune-corpus passages for the application pipeline."""
        from .chunking import load_chunks
        from .retrieval import DenseIndex

        if isinstance(k, bool) or not isinstance(k, int) or k < 0:
            raise ValueError("k must be a non-negative integer")
        if k == 0:
            return []
        if not hasattr(MemoryStore, "_index"):
            MemoryStore._index = DenseIndex(load_chunks(600, 80), name="app")
        return [chunk.text for chunk in MemoryStore._index.search(query, k=k)]

    def forget(self, handle: str) -> bool:
        """Permanently delete a fact by handle; report whether it existed."""
        remaining = [fact for fact in self.facts if fact.handle != handle]
        if len(remaining) == len(self.facts):
            return False
        self.facts = remaining
        self.save()
        return True

    def open_case(self, subject: str) -> str:
        """Create a 90-day case and return its opaque handle."""
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

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "facts": [vars(fact) for fact in self.facts],
            "cases": self.cases,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "MemoryStore":
        """Load, migrate legacy records, and lazily remove expired records."""
        store = cls(path=path)
        if not path.exists():
            return store

        data = json.loads(path.read_text(encoding="utf-8"))
        now = _utcnow()
        changed = False

        for raw_record in data.get("facts", []):
            record = dict(raw_record)
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
