"""Security package: permissions + hooks + audit + guarded execution."""

from magoco_core.security.audit import AuditEvent, AuditLog
from magoco_core.security.executor import GuardedExecutor, default_executor
from magoco_core.security.hooks import HookDenied, HookEngine, default_hooks, register_builtin_guards
from magoco_core.security.permissions import (
    Decision,
    Effect,
    PermissionEngine,
    Rule,
    default_policy,
    tool_to_action_resource,
)

__all__ = [
    "AuditEvent", "AuditLog",
    "GuardedExecutor", "default_executor",
    "HookDenied", "HookEngine", "default_hooks", "register_builtin_guards",
    "Decision", "Effect", "PermissionEngine", "Rule",
    "default_policy", "tool_to_action_resource",
]
