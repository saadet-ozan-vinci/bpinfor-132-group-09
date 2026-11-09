from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.memory import MemoryStore


def test_write_returns_opaque_handle_and_persists_expiration(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(path)

    handle = store.write("A. Muller", "maintenance", "Broken heater")

    assert handle.startswith("fact-")
    UUID(handle.removeprefix("fact-"))
    record = json.loads(path.read_text(encoding="utf-8"))["facts"][0]
    written_at = datetime.fromisoformat(
        record["written_at"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(
        record["expires_at"].replace("Z", "+00:00"))
    assert expires_at - written_at == timedelta(days=90)


def test_personal_search_is_scoped_limited_and_keeps_conflicts(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")
    store.write("A. Muller", "maintenance", "Heater is broken")
    store.write("A. Muller", "maintenance", "Heater has been repaired")
    store.write("B. Muller", "maintenance", "Heater is broken")

    assert store.search_memory("A. Muller", "heater", k=1) == [
        "Heater is broken",
    ]
    assert store.search_memory("A. Muller", "heater", k=3) == [
        "Heater is broken",
        "Heater has been repaired",
    ]
    assert store.search_memory("A. Muller", "heater", k=0) == []


def test_forget_deletes_only_stored_fact(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")
    handle = store.write("A. Muller", "maintenance", "Broken heater")

    assert store.forget(handle) is True
    assert store.forget(handle) is False
    assert store.search_memory("A. Muller", "heater") == []


def test_expired_records_are_removed_on_load_and_legacy_records_migrate(
        tmp_path):
    path = tmp_path / "memory.json"
    now = datetime.now(timezone.utc)
    expired = (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    written_at = (now - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    path.write_text(json.dumps({
        "facts": [
            {
                "subject": "A. Muller",
                "kind": "maintenance",
                "text": "old fact",
                "handle": "fact-old",
                "written_at": expired,
                "expires_at": expired,
            },
            {
                "subject": "A. Muller",
                "kind": "maintenance",
                "text": "recent fact",
                "handle": "fact-recent",
                "written_at": written_at,
            },
        ],
        "cases": {
            "case-old": {"subject": "A. Muller", "expires_at": expired},
            "case-live": "B. Muller",
        },
    }), encoding="utf-8")

    store = MemoryStore.load(path)

    assert [fact.text for fact in store.facts] == ["recent fact"]
    assert store.subject_of("case-old") is None
    assert store.subject_of("case-live") == "B. Muller"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert [fact["text"] for fact in saved["facts"]] == ["recent fact"]
    assert "case-old" not in saved["cases"]
    assert "expires_at" in saved["facts"][0]
    assert "expires_at" in saved["cases"]["case-live"]


def test_open_case_persists_uuid_handle_and_expiration(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(path)

    handle = store.open_case("A. Muller")

    assert handle.startswith("case-")
    UUID(handle.removeprefix("case-"))
    loaded = MemoryStore.load(path)
    assert loaded.subject_of(handle) == "A. Muller"
    expires = datetime.fromisoformat(
        loaded.cases[handle]["expires_at"].replace("Z", "+00:00"))
    assert expires > datetime.now(timezone.utc) + timedelta(days=89)


def test_pipeline_search_keeps_using_the_week7_index(monkeypatch):
    class Index:
        def search(self, query, k):
            assert query == "collection schedule"
            assert k == 2
            return [type("Chunk", (), {"text": "corpus passage"})()]

    monkeypatch.setattr(MemoryStore, "_index", Index(), raising=False)

    assert MemoryStore().search("A. Muller", "collection schedule", k=2) == [
        "corpus passage",
    ]
