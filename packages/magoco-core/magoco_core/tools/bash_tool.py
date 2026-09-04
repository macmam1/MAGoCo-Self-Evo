"""Bash execution tool with timeout + output truncation.

Deterministic dangerous-command blocking lives in security/hooks.py;
this tool focuses on safe execution (timeout, cwd, truncation).
"""

from __future__ import annotations

import subprocess
from typing import Any

from magoco_core.tools.registry import Tool, ToolResult, tool_registry

MAX_OUTPUT_CHARS = 50_000
MAX_OUTPUT_LINES = 2000


class BashExecTool(Tool):
    @property
    def name(self) -> str:
        return "bash_exec"

    @property
    def description(self) -> str:
        return "Run a shell command with timeout. Returns stdout/stderr truncated."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
                "timeout": {"type": "number", "description": "Timeout seconds", "default": 30},
                "cwd": {"type": "string", "description": "Working directory", "default": "/tmp"},
            },
            "required": ["command"],
        }

    async def execute(self, command: str, timeout: float = 30, cwd: str = "/tmp") -> ToolResult:
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=min(timeout, 120), cwd=cwd or "/tmp",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, content="", error=f"Timeout after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

        out = proc.stdout or ""
        err = proc.stderr or ""
        lines = out.splitlines()
        if len(lines) > MAX_OUTPUT_LINES:
            out = "\n".join(lines[:MAX_OUTPUT_LINES]) + f"\n...[truncated {len(lines) - MAX_OUTPUT_LINES} lines]"
        if len(out) > MAX_OUTPUT_CHARS:
            out = out[:MAX_OUTPUT_CHARS] + "...[truncated]"
        if len(err) > 5000:
            err = err[:5000] + "...[truncated]"

        if proc.returncode == 0:
            return ToolResult(success=True, content=out, metadata={"exit_code": 0})
        return ToolResult(success=False, content=out, error=err or f"exit {proc.returncode}",
                          metadata={"exit_code": proc.returncode})


tool_registry.register(BashExecTool())
