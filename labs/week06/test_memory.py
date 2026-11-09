from datetime import datetime, timedelta, timezone
import json
from uuid import UUID

from labs.week06.starter.memory import MemoryStore


def test_write_returns_uuid_and_persists_90_day_expiration(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(path)

    handle = store.write("A. Muller", "maintenance", "Broken heater")

    assert handle.startswith("fact-")
    UUID(handle.removeprefix("fact-"))
    record = json.loads(path.read_text(encoding="utf-8"))["facts"][0]
    written_at = datetime.fromisoformat(record["written_at"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    assert expires_at - written_at == timedelta(days=90)


def test_search_is_subject_scoped_and_keeps_conflicting_facts(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")
    store.write("A. Muller", "maintenance", "Heater is broken")
    store.write("A. Muller", "maintenance", "Heater has been repaired")
    store.write("B. Muller", "maintenance", "Heater is broken")

    assert store.search("A. Muller", "heater", k=3) == [
        "Heater is broken",
        "Heater has been repaired",
    ]


def test_load_lazily_removes_expired_facts_and_cases(tmp_path):
    path = tmp_path / "memory.json"
    now = datetime.now(timezone.utc)
    expired = (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    data = {
        "facts": [{
            "subject": "A. Muller",
            "kind": "maintenance",
            "text": "old fact",
            "handle": "fact-old",
            "written_at": expired,
            "expires_at": expired,
        }],
        "cases": {
            "case-old": {"subject": "A. Muller", "expires_at": expired},
            "case-live": {
                "subject": "B. Muller",
                "expires_at": (now + timedelta(days=1)).isoformat(),
            },
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")

    store = MemoryStore.load(path)

    assert store.facts == []
    assert store.subject_of("case-old") is None
    assert store.subject_of("case-live") == "B. Muller"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["facts"] == []
    assert "case-old" not in saved["cases"]


def test_legacy_records_are_migrated_with_safe_expiration(tmp_path):
    path = tmp_path / "memory.json"
    now = datetime.now(timezone.utc)
    written_at = (now - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    path.write_text(json.dumps({
        "facts": [{
            "subject": "A. Muller",
            "kind": "maintenance",
            "text": "recent fact",
            "handle": "fact-recent",
            "written_at": written_at,
        }],
        "cases": {"case-legacy": "A. Muller"},
    }), encoding="utf-8")

    store = MemoryStore.load(path)

    assert len(store.facts) == 1
    assert store.subject_of("case-legacy") == "A. Muller"
    migrated = json.loads(path.read_text(encoding="utf-8"))
    assert "expires_at" in migrated["facts"][0]
    assert "expires_at" in migrated["cases"]["case-legacy"]
    assert datetime.fromisoformat(
        migrated["cases"]["case-legacy"]["expires_at"].replace(
            "Z", "+00:00")
    ) > now + timedelta(days=89)


def test_case_handle_is_uuid_and_expires_after_90_days(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(path)

    handle = store.open_case("A. Muller")

    assert handle.startswith("case-")
    UUID(handle.removeprefix("case-"))
    loaded = MemoryStore.load(path)
    assert loaded.subject_of(handle) == "A. Muller"
    expires = loaded.cases[handle]["expires_at"]
    opened = datetime.fromisoformat(
        json.loads(path.read_text(encoding="utf-8"))["cases"][handle][
            "expires_at"
        ].replace("Z", "+00:00")
    )
    assert isinstance(expires, str)
    assert opened > datetime.now(timezone.utc) + timedelta(days=89)
