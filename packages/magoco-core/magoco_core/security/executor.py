"""Guarded executor: permission check + Pre/Post hooks + audit around any tool call."""

from __future__ import annotations

from typing import Any

from magoco_core.security.audit import AuditLog
from magoco_core.security.hooks import (
    POST_TOOL_USE,
    POST_TOOL_USE_FAILURE,
    PRE_TOOL_USE,
    HookDenied,
    HookEngine,
    default_hooks,
)
from magoco_core.security.permissions import (
    Effect,
    PermissionEngine,
    default_policy,
    tool_to_action_resource,
)
from magoco_core.tools.registry import ToolResult, tool_registry


class GuardedExecutor:
    """Wraps ToolRegistry with deterministic security.

    - DENY -> blocked, audited
    - ASK + strict -> approval-required failure (non-interactive safe)
    - ASK + auto_approve -> allowed but audited (backward-compat for existing flows)
    - PreToolUse hooks can still block even allowed calls (defense in depth)
    """

    def __init__(
        self,
        permissions: PermissionEngine | None = None,
        hooks: HookEngine | None = None,
        audit: AuditLog | None = None,
        actor: str = "agent",
        strict: bool = False,
        auto_approve_ask: bool = True,
    ):
        self.permissions = permissions or default_policy()
        self.hooks = hooks or default_hooks()
        self.audit = audit or AuditLog()
        self.actor = actor
        self.strict = strict
        self.auto_approve_ask = auto_approve_ask

    async def run(self, tool_name: str, args: dict[str, Any] | None = None) -> ToolResult:
        args = args or {}
        action, resource = tool_to_action_resource(tool_name, args)
        decision = self.permissions.check(action, resource)

        if decision.effect == Effect.DENY:
            self.audit.log(self.actor, action, resource, "deny", decision.message)
            return ToolResult(success=False, content="", error=f"Denied by policy: {decision.message}")

        if decision.effect == Effect.ASK and self.strict and not self.auto_approve_ask:
            self.audit.log(self.actor, action, resource, "ask", "approval required (strict)")
            return ToolResult(success=False, content="", error="Approval required (strict mode)")

        # Pre hooks (deterministic enforcement — cannot be skipped by the model)
        try:
            self.hooks.emit(PRE_TOOL_USE, {"tool_name": tool_name, "action": action,
                                           "path": args.get("path", ""), "command": args.get("command", args.get("code", "")),
                                           "input": str(args)})
        except HookDenied as e:
            self.audit.log(self.actor, action, resource, "hook-deny", e.reason)
            return ToolResult(success=False, content="", error=f"Blocked by hook: {e.reason}")

        tool = tool_registry.get(tool_name)
        if not tool:
            return ToolResult(success=False, content="", error=f"Tool '{tool_name}' not found")

        try:
            result = await tool.execute(**args)
        except TypeError as e:
            return ToolResult(success=False, content="", error=f"Bad args for {tool_name}: {e}")

        event = POST_TOOL_USE if result.success else POST_TOOL_USE_FAILURE
        try:
            self.hooks.emit(event, {"tool_name": tool_name, "action": action, "success": result.success})
        except HookDenied:
            pass  # post-hooks observe; a deny here must not rewrite history

        eff = decision.effect.value + ("+auto" if decision.effect == Effect.ASK and self.auto_approve_ask else "")
        self.audit.log(self.actor, action, resource, eff, f"tool={tool_name} ok={result.success}")
        return result


# Shared default executor (backward-compatible: audits, enforces denies+hooks)
default_executor = GuardedExecutor()
