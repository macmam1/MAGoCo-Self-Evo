"""Deterministic risk scoring for tool calls — professional HITL foundation.

Risk levels drive UX, not just policy:
- low: read-only, reversible (auto-approvable in non-strict flows)
- medium: writes scoped to workspace (ask, one-click approve)
- high: shell execution, broad writes, network exfiltration shapes (ask + show full command)
- critical: destructive/secret-touching shapes (auto-deny, even if policy says ask)

Critical patterns ALWAYS deny — defense in depth beneath PermissionEngine rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing Any, Dict, List


@dataclass
class RiskAssessment:
    level: str  # low | medium | high | critical
    score: int  # 0-100
    reasons: List[str] = field(default_factory=list)
    auto_deny: bool = False


_CRITICAL_SHELL = [
    (r"\brm\s+-rf\s+/", "rm -rf on root"),
    (r"\brm\s+-rf\s+~", "rm -rf on home"),
    (r"\bmkfs\b", "filesystem format"),
    (r"\bdd\s+.*of=/dev/", "raw disk write"),
    (r":\(\)\s*{\s*:\|:\s*&\s*}\s*;", "fork bomb"),
    (r"\bchmod\s+-R\s+777\s+/", "chmod 777 on root"),
    (r"\bcurl\b.*\|\s*(sh|bash)", "remote code execution pipe"),
    (r"\bwget\b.*\|\s*(sh|bash)", "remote code execution pipe"),
]

_HIGH_SIGNALS = [
    (r"\bsudo\b", "privilege escalation"),
    (r"\bchmod\b|\bchown\b", "permission change"),
    (r"\bssh\b|\bscp\b", "remote host access"),
    (r"\bdocker\b|\bkubectl\b", "container/cluster control"),
    (r"\bgit\s+push\b", "publishes history"),
    (r"\bnpm\s+publish\b|\bpip\s+upload\b|\btwine\b", "package publish"),
    (r">\s*/etc/|>\s*~/.ssh/", "write to system/ssh paths"),
]

_SECRET_PATHS = [".env", ".pem", ".key", "id_rsa", "id_ed25519", "credentials", "secrets"]


def assess(action: str, resource: str = "*", args: Dict[str, Any] | None = None) -> RiskAssessment:
    """Score a tool call deterministically. Pure function — unit-testable."""
    args = args or {}
    text = f"{action} {resource} {args.get('command', '')} {args.get('code', '')} {args.get('path', '')} {args.get('url', '')}"
    reasons: List[str] = []
    score = 0

    # Secrets touch = critical, always deny
    lowered = text.lower()
    for secret in _SECRET_PATHS:
        if secret in lowered and action in ("read", "edit"):
            return RiskAssessment("critical", 100, [f"touches secret material: {secret}"], auto_deny=True)

    # Critical shell shapes
    blob = f"{args.get('command', '')} {args.get('code', '')} {resource}"
    for pattern, reason in _CRITICAL_SHELL:
        if re.search(pattern, blob):
            return RiskAssessment("critical", 100, [reason], auto_deny=True)

    # Base by action
    base = {"read": 5, "glob": 5, "grep": 5, "websearch": 10, "webfetch": 15,
            "edit": 45, "shell": 70, "subagent": 40, "skill": 40}.get(action, 50)
    score += base
    reasons.append(f"base:{action}={base}")

    for pattern, reason in _HIGH_SIGNALS:
        if re.search(pattern, blob):
            score += 20
            reasons.append(reason)

    # Network exfiltration shape: shell + URL + upload verbs
    if action == "shell" and re.search(r"https?://", blob) and re.search(r"\b(post|put|upload|send|exfil)\b", blob, re.I):
        score += 20
        reasons.append("possible exfiltration shape")

    score = min(100, score)
    level = "low" if score < 25 else ("medium" if score < 55 else ("high" if score < 85 else "critical"))
    return RiskAssessment(level, score, reasons, auto_deny=(level == "critical"))
