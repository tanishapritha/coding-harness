from pathlib import Path

import pytest

from harness.workspace import Workspace


def test_workspace_write_and_read(tmp_path: Path):
    workspace = Workspace(tmp_path)
    workspace.write_file("src/main.py", "print('ok')")
    assert workspace.read_file("src/main.py") == "print('ok')"


def test_workspace_rejects_escape(tmp_path: Path):
    workspace = Workspace(tmp_path)
    with pytest.raises(PermissionError):
        workspace.read_file("../outside.txt")
