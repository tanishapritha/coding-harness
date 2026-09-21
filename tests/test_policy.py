from harness.policy import PolicyEngine


def test_blocks_absolute_paths():
    decision = PolicyEngine().check("read_file", {"path": "/etc/passwd"})
    assert not decision.allowed


def test_blocks_traversal():
    decision = PolicyEngine().check("read_file", {"path": "../secret.txt"})
    assert not decision.allowed


def test_blocks_credentials():
    decision = PolicyEngine().check("read_file", {"path": ".env"})
    assert not decision.allowed


def test_blocks_destructive_commands():
    decision = PolicyEngine().check("run_command", {"command": "rm -rf /"})
    assert not decision.allowed


def test_allows_normal_actions():
    decision = PolicyEngine().check("read_file", {"path": "src/main.py"})
    assert decision.allowed
