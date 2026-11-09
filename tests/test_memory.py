from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from app import pipeline
from app import agent, agents
from app.memory import MemoryStore
from project.trace import TraceRecorder, local_conditions


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


class MemorySelectionClient:
    def __init__(self, memories):
        content = json.dumps({"memories": memories})
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(
                        content=content))],
                    usage=SimpleNamespace(
                        prompt_tokens=12, completion_tokens=8),
                )))


def _run_for_memory_test(tmp_path, monkeypatch, client):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    recorder = TraceRecorder(
        week=6, case_id="memory-test",
        conditions=local_conditions("none"), user_input="test")
    run = pipeline._Run(recorder, "memory-test", unattended=True)
    run.client = client
    return run


def test_pipeline_uses_model_to_save_quoted_memories_for_subject(
        tmp_path, monkeypatch):
    text = "My name is Alex. I like tea."
    client = MemorySelectionClient([
        {"kind": "profile", "quote": "My name is Alex"},
        {"kind": "preference", "quote": "I like tea"},
        {"kind": "profile", "quote": "I live in Luxembourg"},
    ])
    run = _run_for_memory_test(tmp_path, monkeypatch, client)

    pipeline._remember(run, "A. Muller", text)

    store = MemoryStore.load(tmp_path / "artifacts" / "memory_store.json")
    assert [(fact.kind, fact.text) for fact in store.facts] == [
        ("profile", "My name is Alex"),
        ("preference", "I like tea"),
    ]
    assert run.models


def test_pipeline_retrieves_personal_memory_and_corpus_together(
        tmp_path, monkeypatch):
    class Index:
        def search(self, query, k):
            return [SimpleNamespace(text="commune corpus passage")]

    monkeypatch.setattr(MemoryStore, "_index", Index(), raising=False)
    run = _run_for_memory_test(tmp_path, monkeypatch, client=None)
    store = MemoryStore(tmp_path / "artifacts" / "memory_store.json")
    store.write("A. Muller", "profile", "My name is Alex")

    facts = pipeline._recall(run, "A. Muller", "What is my name?")

    assert facts == [
        "commune corpus passage",
        "Remembered profile: My name is Alex",
    ]


def test_remembered_language_preference_overrides_question_language():
    assert "remembered user" in agent.SYSTEM
    assert "takes precedence" in agent.SYSTEM
    assert "explicit remembered language preference" in agents.REVIEW_PROMPT
    assert "honor that" in agents.REVIEW_PROMPT
