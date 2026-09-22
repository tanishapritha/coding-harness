from pathlib import Path
from harness.memory.sqlite import SQLiteMemory


def test_memory_round_trip(tmp_path: Path):
    store = SQLiteMemory(tmp_path / "forge.db", "repo-a")
    store.remember("Integration tests require Redis", "run-1", 0.9)
    results = store.search("Redis integration tests")
    assert len(results) == 1
    assert results[0]["content"] == "Integration tests require Redis"


def test_memory_is_repository_scoped(tmp_path: Path):
    db = tmp_path / "forge.db"
    a = SQLiteMemory(db, "repo-a")
    b = SQLiteMemory(db, "repo-b")
    a.remember("repo A uses Redis")
    assert b.search("Redis") == []


def test_memory_deduplicates(tmp_path: Path):
    store = SQLiteMemory(tmp_path / "forge.db", "repo-a")
    store.remember("same fact", confidence=0.5)
    store.remember("same fact", confidence=0.9)
    rows = store.all()
    assert len(rows) == 1
    assert rows[0]["confidence"] == 0.9
