from pathlib import Path
from harness.context.engine import ContextEngine
from harness.memory.sqlite import SQLiteMemory
from harness.workspace import Workspace


def test_context_retrieves_relevant_file(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def authenticate(token): return True", encoding="utf-8")
    (tmp_path / "tests" / "test_auth.py").write_text("def test_authenticate(): pass", encoding="utf-8")
    (tmp_path / "README.md").write_text("unrelated documentation", encoding="utf-8")
    memory = SQLiteMemory(tmp_path / "memory.db", str(tmp_path).lower())
    memory.remember("authentication uses tokens")
    bundle = ContextEngine(Workspace(tmp_path), memory).build("fix authentication token tests")
    paths = [f.path for f in bundle.files]
    assert "src/auth.py" in paths or "tests/test_auth.py" in paths
    assert bundle.memories[0]["content"] == "authentication uses tokens"


def test_context_has_token_budget(tmp_path: Path):
    (tmp_path / "large.py").write_text("# auth token\n" + "x = 1\n" * 5000, encoding="utf-8")
    bundle = ContextEngine(Workspace(tmp_path), None, max_files=10, max_file_chars=1000).build("auth token", token_budget=1000)
    assert bundle.token_estimate <= 1000
