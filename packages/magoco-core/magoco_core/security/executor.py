"""Guarded executor: permission check + Pre/Post hooks + audit around any tool call.

Two modes:
- run(): legacy, non-blocking (ASK auto-approves unless strict). Unchanged behavior.
- run_gated(): professional HITL — ASK pauses, creates a reviewable approval
  (with tool args + risk score + expiry), waits for human decision, then
  proceeds or aborts. Nothing executes while pending.
"""

from __future__ import annotations

import asyncio
import time
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

    async def run_gated(self, tool_name: str, args: dict[str, Any] | None = None,
                        session_id: str = "", timeout: float = 600.0,
                        poll_interval: float = 2.0, ttl_seconds: int = 600,
                        purpose: str = "", lang: str = "en",
                        trust_relax: bool = False) -> ToolResult:
        """Blocking HITL execution: ASK waits for human approval, then proceeds.

        - DENY (policy or risk auto-deny) -> blocked immediately, audited.
        - ALLOW -> executes directly (still audited + hooked).
        - ASK -> approval created (tool+args+risk+expiry+plain-language
          explanation in en+fa + the model's own purpose statement), polls
          store until approved / rejected / expired / timeout. Approved resumes
          execution; anything else aborts WITHOUT running the tool.
        """
        from magoco_core.security.risk import assess
        from magoco_core.security.explain import explain_tool_call
        args = args or {}
        action, resource = tool_to_action_resource(tool_name, args)
        decision = self.permissions.check(action, resource)
        risk = assess(action, resource, args)

        if decision.effect == Effect.DENY or risk.auto_deny:
            reason = f"risk:{risk.level} {','.join(risk.reasons)}" if risk.auto_deny else decision.message
            self.audit.log(self.actor, action, resource, "deny", f"tool={tool_name} {reason}")
            return ToolResult(success=False, content="",
                              error=f"Denied ({risk.level}): {reason}",
                              metadata={"risk": risk.level, "score": risk.score})

        if decision.effect == Effect.ALLOW and risk.level == "low":
            return await self.run(tool_name, args)

        # Earned autonomy (opt-in): verified track record relaxes ASK -> allow.
        # Never overrides DENY or critical auto-deny above. Audited either way.
        if decision.effect == Effect.ASK and trust_relax and not risk.auto_deny:
            from magoco_core.security.trust import get_trust_registry
            verdict = get_trust_registry().should_relax(self.actor, action)
            if verdict["relax"]:
                self.audit.log(self.actor, action, resource, "allow-by-trust",
                               f"tool={tool_name} ok={verdict['verified_ok']}/{verdict['verified_total']}")
                return await self.run(tool_name, args)

        # ASK path (or ALLOW+elevated risk): create reviewable approval and wait.
        # The card always carries a plain-language explanation (en+fa) so that
        # beginners understand the command, plus the model's own purpose statement.
        from magoco_core.evolution.approvals_store import get_approvals_store
        store = get_approvals_store()
        explanation = {
            "en": explain_tool_call(tool_name, args, "en"),
            "fa": explain_tool_call(tool_name, args, "fa"),
            "model_purpose": purpose or "",
        }
        req = store.create(
            agent_name=self.actor,
            action_description=f"{tool_name} {action}:{resource} [risk:{risk.level} {risk.score}]",
            proposed_input={"tool": tool_name, "args": args, "session_id": session_id,
                            "explanation": explanation},
            tool_name=tool_name, args=args, action=action, resource=resource,
            session_id=session_id, risk=risk.level, risk_score=risk.score,
            ttl_seconds=ttl_seconds,
        )
        self.audit.log(self.actor, action, resource, "ask-wait",
                       f"tool={tool_name} approval={req['request_id']} risk={risk.level}")
        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(poll_interval)
            current = store.get(req["request_id"])
            if not current:
                return ToolResult(success=False, content="", error="Approval vanished; aborted")
            status = current.get("status")
            if status == "approved":
                self.audit.log(self.actor, action, resource, "ask-approved",
                               f"tool={tool_name} approval={req['request_id']}")
                result = await self.run(tool_name, args)
                try:
                    from magoco_core.security.trust import get_trust_registry
                    get_trust_registry().record(self.actor, action, ok=result.success, verified=True)
                except Exception:
                    pass
                return result
            if status in ("rejected", "skipped", "expired"):
                self.audit.log(self.actor, action, resource, f"ask-{status}",
                               f"tool={tool_name} approval={req['request_id']}")
                return ToolResult(success=False, content="",
                                  error=f"Blocked by human ({status}): {current.get('comment') or 'no comment'}",
                                  metadata={"approval_id": req["request_id"], "status": status})
        store.resolve(req["request_id"], "expired", comment="gated wait timed out")
        self.audit.log(self.actor, action, resource, "ask-timeout",
                       f"tool={tool_name} approval={req['request_id']}")
        return ToolResult(success=False, content="", error="Approval timed out; aborted without executing",
                          metadata={"approval_id": req["request_id"], "status": "expired"})


# Shared default executor (backward-compatible: audits, enforces denies+hooks)
default_executor = GuardedExecutor()
