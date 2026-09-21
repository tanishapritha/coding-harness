from harness.state import RunState


def test_state_transition():
    state = RunState("abc", "task", "/tmp/project")
    assert state.status == "CREATED"
    state.transition("EXECUTING")
    assert state.status == "EXECUTING"
    assert state.as_dict()["run_id"] == "abc"
