"""Permission Engine — allow/ask/deny per action+resource.

Modeled on OpenCode V2 permissions + Claude Code rule syntax:
  Rule(action, resource_pattern, effect), last match wins, default = ask.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass(frozen=True)
class Rule:
    action: str  # e.g. read, edit, shell, webfetch, websearch, skill, subagent, mcp__srv__tool
    resource: str  # fnmatch pattern; shell pattern ending " *" also matches bare command
    effect: Effect


@dataclass
class Decision:
    effect: Effect
    rule: Rule | None = None
    message: str = ""


def _match(pattern: str, value: str) -> bool:
    if fnmatch.fnmatchcase(value, pattern):
        return True
    # shell convenience: "git diff *" also matches bare "git diff"
    if pattern.endswith(" *") and value == pattern[:-2]:
        return True
    return False


@dataclass
class PermissionEngine:
    rules: list[Rule] = field(default_factory=list)

    def check(self, action: str, resource: str = "*") -> Decision:
        hit: Rule | None = None
        for r in self.rules:
            if r.action != action and r.action != "*":
                continue
            if _match(r.resource, resource):
                hit = r  # last match wins
        if hit is None:
            return Decision(Effect.ASK, None, f"no rule matched {action}:{resource} -> ask")
        return Decision(hit.effect, hit, f"{hit.effect.value} by {hit.action}:{hit.resource}")

    def allow(self, action: str, resource: str = "*") -> "PermissionEngine":
        self.rules.append(Rule(action, resource, Effect.ALLOW))
        return self

    def deny(self, action: str, resource: str = "*") -> "PermissionEngine":
        self.rules.append(Rule(action, resource, Effect.DENY))
        return self

    def ask(self, action: str, resource: str = "*") -> "PermissionEngine":
        self.rules.append(Rule(action, resource, Effect.ASK))
        return self


def default_policy() -> PermissionEngine:
    """Secure-by-default baseline: read-friendly, write/shell gated, secrets blocked."""
    e = PermissionEngine()
    # secrets first (can be overridden later by explicit allow — last wins)
    e.deny("read", "*.env").deny("read", "*.env.*").deny("read", "*/.env")
    e.deny("edit", "*.env").deny("edit", "*.env.*").deny("edit", "*/.env")
    e.allow("read", "*.env.example")
    # read-friendly
    e.allow("read", "*").allow("glob", "*").allow("grep", "*")
    e.allow("webfetch", "*").allow("websearch", "*")
    # gated
    e.ask("edit", "*").ask("shell", "*").ask("subagent", "*").ask("skill", "*")
    return e


def tool_to_action_resource(tool_name: str, args: dict) -> tuple[str, str]:
    """Map a tool call to (action, resource) for permission checks."""
    if tool_name in ("file_read", "file_list"):
        return ("read", str(args.get("path", "*")))
    if tool_name in ("file_write",):
        return ("edit", str(args.get("path", "*")))
    if tool_name in ("bash_exec", "python_exec"):
        return ("shell", str(args.get("command", args.get("code", "*"))))
    if tool_name == "web_search":
        return ("websearch", str(args.get("query", "*")))
    if tool_name == "web_fetch":
        return ("webfetch", str(args.get("url", "*")))
    if tool_name.startswith("mcp__"):
        return (tool_name, str(args))
    return (tool_name, "*")
