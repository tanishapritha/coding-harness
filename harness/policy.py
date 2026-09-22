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
]

PROTECTED_PATHS = {".env", ".env.local", ".env.production"}


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    def check(self, tool: str, arguments: dict) -> PolicyDecision:
        if tool in {"read_file", "write_file"}:
            path = str(arguments.get("path", "")).replace("\\", "/")
            parts = [part for part in path.split("/") if part not in ("", ".")]
            if path.startswith("/") or (parts and parts[0] == "..") or ".." in parts:
                return PolicyDecision(False, "path must stay inside workspace")
            normalized = "/".join(parts)
            if normalized in PROTECTED_PATHS or normalized.startswith(".ssh/"):
                return PolicyDecision(False, "protected credential path")
        if tool == "run_command":
            command = str(arguments.get("command", ""))
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return PolicyDecision(False, "blocked by command policy")
        return PolicyDecision(True, "allowed")
