from __future__ import annotations

import re
from dataclasses import dataclass

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+[/~]",
    r"git\s+(reset|clean|checkout)\b",
    r"git\s+push\b",
    r"curl\s+[^|]+\|\s*(bash|sh)",
    r"wget\s+[^|]+\|\s*(bash|sh)",
    r"chmod\s+777",
    r"\.ssh/",
    r"\.env(?:\s|$)",
]


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    def check(self, tool: str, arguments: dict) -> PolicyDecision:
        if tool == "run_command":
            command = str(arguments.get("command", ""))
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return PolicyDecision(False, f"blocked by command policy: {pattern}")
        if tool in {"read_file", "write_file"}:
            path = str(arguments.get("path", ""))
            if path.startswith("/") or ".." in path.replace("\\", "/").split("/"):
                return PolicyDecision(False, "path must stay inside workspace")
        return PolicyDecision(True, "allowed")
