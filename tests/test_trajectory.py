import json
from harness.state import RunState
from harness.trajectories.store import TrajectoryStore


def test_trajectory_persists_run(tmp_path):
    store = TrajectoryStore(tmp_path)
    state = RunState("abc123", "fix auth", "/repo")
    state.transition("COMPLETED")
    path = store.save_run(state)
    assert (path / "state.json").exists()
    data = json.loads((path / "state.json").read_text())
    assert data["run_id"] == "abc123"
