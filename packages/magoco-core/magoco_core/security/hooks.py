"""Hook Engine — deterministic lifecycle events.

Events (core 10): SessionStart, PreToolUse, PostToolUse, PostToolUseFailure,
FileChanged, SessionEnd + TaskCreated/TaskCompleted, SubagentStart/Stop.
Handlers: python callables or shell commands (exit 2 = block, stderr = reason).
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable


class HookDenied(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# Core events
SESSION_START = "SessionStart"
PRE_TOOL_USE = "PreToolUse"
POST_TOOL_USE = "PostToolUse"
POST_TOOL_USE_FAILURE = "PostToolUseFailure"
FILE_CHANGED = "FileChanged"
SESSION_END = "SessionEnd"
TASK_CREATED = "TaskCreated"
TASK_COMPLETED = "TaskCompleted"
SUBAGENT_START = "SubagentStart"
SUBAGENT_STOP = "SubagentStop"


@dataclass
class Hook:
    event: str
    matcher: str = "*"  # tool name or "*" ; for FileChanged a glob watchlist
    kind: str = "callable"  # callable | command
    fn: Callable[[dict], Any] | None = None
    command: str = ""
    timeout: float = 10.0


def _match(matcher: str, value: str) -> bool:
    if matcher in ("*", "", value):
        return True
    if any(c not in matcher for c in (",", "|")) and set(matcher) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_ -|,"):
        # exact list with , or |
        for part in matcher.replace("|", ",").split(","):
            if part.strip() == value:
                return True
        return False
    try:
        return fnmatch.fnmatchcase(value, matcher)
    except Exception:
        return False


@dataclass
class HookEngine:
    hooks: list[Hook] = field(default_factory=list)

    def on(self, event: str, matcher: str = "*", fn: Callable[[dict], Any] | None = None,
           command: str | None = None, timeout: float = 10.0) -> "HookEngine":
        if command:
            self.hooks.append(Hook(event, matcher, "command", None, command, timeout))
        else:
            self.hooks.append(Hook(event, matcher, "callable", fn, "", timeout))
        return self

    def emit(self, event: str, payload: dict) -> list[Any]:
        """Run matching hooks in order. Raises HookDenied on block."""
        results = []
        key = payload.get("tool_name", "") or payload.get("path", "") or ""
        for h in self.hooks:
            if h.event != event:
                continue
            if not _match(h.matcher, key):
                continue
            if h.kind == "callable" and h.fn is not None:
                out = h.fn(dict(payload))
                if out is False:
                    raise HookDenied(f"blocked by hook {event}:{h.matcher}")
                results.append(out)
            elif h.kind == "command":
                proc = subprocess.run(
                    h.command, shell=True, input=json.dumps(payload),
                    capture_output=True, text=True, timeout=h.timeout,
                )
                if proc.returncode == 2:
                    raise HookDenied(proc.stderr.strip() or f"blocked by hook {event}:{h.matcher}")
                results.append(proc.stdout.strip())
        return results


# --- Built-in deterministic guards ---

DANGEROUS_SHELL_PATTERNS = [
    "rm -rf /", "rm -rf /*", "rm -rf ~", ":(){", "mkfs", "dd if=",
    "shutdown", "reboot", "halt", "poweroff",
]

SECRET_PATH_HINTS = (".env",)


def _guard_dangerous_shell(payload: dict) -> bool:
    cmd = str(payload.get("input", "") or payload.get("command", "") or "")
    low = cmd.lower()
    for pat in DANGEROUS_SHELL_PATTERNS:
        if pat in low:
            return False
    # pipe-to-shell from network is high risk: `curl ... | sh`
    if ("curl" in low or "wget" in low) and "| sh" in low.replace("  ", " "):
        return False
    if ("curl" in low or "wget" in low) and "| bash" in low:
        return False
    return True


def _guard_secret_write(payload: dict) -> bool:
    path = str(payload.get("path", "") or "")
    if path.endswith(".env") or "/.env" in path or path.endswith(".env.local"):
        return False
    return True


def register_builtin_guards(engine: HookEngine) -> HookEngine:
    engine.on(PRE_TOOL_USE, "bash_exec", fn=_guard_dangerous_shell)
    engine.on(PRE_TOOL_USE, "python_exec", fn=_guard_dangerous_shell)
    engine.on(PRE_TOOL_USE, "shell", fn=_guard_dangerous_shell)
    engine.on(PRE_TOOL_USE, "file_write", fn=_guard_secret_write)
    engine.on(PRE_TOOL_USE, "edit", fn=_guard_secret_write)
    return engine


def default_hooks() -> HookEngine:
    return register_builtin_guards(HookEngine())
