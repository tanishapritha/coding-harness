from pathlib import Path

from harness.cloud.workspaces import DockerWorkspaceManager


def test_workspace_manager_root(tmp_path: Path):
    manager = DockerWorkspaceManager(tmp_path)
    assert manager.root == tmp_path.resolve()


def test_workspace_status_missing(tmp_path: Path):
    manager = DockerWorkspaceManager(tmp_path)
    try:
        manager.status("missing")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing workspace should raise")
