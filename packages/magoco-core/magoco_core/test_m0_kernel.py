"""M0 kernel tests: permissions + hooks + guarded tools (Epic #2, #3)."""

import asyncio

from magoco_core.security import (
    Effect,
    GuardedExecutor,
    PermissionEngine,
    default_policy,
)
from magoco_core.security.audit import AuditLog
from magoco_core.security.hooks import HookDenied, HookEngine, default_hooks
from magoco_core.tools import registry as _  # noqa: F401  (auto-register all)
from magoco_core.tools.registry import tool_registry


def test_permission_last_match_wins():
    e = PermissionEngine()
    e.allow("read", "*").deny("read", "*.env")
    assert e.check("read", "app.py").effect == Effect.ALLOW
    assert e.check("read", ".env").effect == Effect.DENY
    e.allow("read", ".env")  # explicit override wins (last match)
    assert e.check("read", ".env").effect == Effect.ALLOW
    print("ok permission last-match-wins")


def test_permission_shell_prefix():
    e = PermissionEngine()
    e.allow("shell", "git diff *")
    assert e.check("shell", "git diff").effect == Effect.ALLOW
    assert e.check("shell", "git diff HEAD").effect == Effect.ALLOW
    assert e.check("shell", "rm -rf /").effect == Effect.ASK
    print("ok shell prefix match")


def test_default_policy_blocks_env():
    e = default_policy()
    assert e.check("read", ".env").effect == Effect.DENY
    assert e.check("edit", ".env").effect == Effect.DENY
    assert e.check("read", "app.py").effect == Effect.ALLOW
    print("ok default policy secrets")


def test_hook_blocks_dangerous_shell():
    h = default_hooks()
    try:
        h.emit("PreToolUse", {"tool_name": "bash_exec", "command": "rm -rf /", "input": "rm -rf /"})
        raise AssertionError("should have blocked")
    except HookDenied:
        print("ok hook blocks rm -rf /")
    # normal command passes
    h.emit("PreToolUse", {"tool_name": "bash_exec", "command": "echo hi", "input": "echo hi"})
    print("ok hook allows normal")


def test_hook_blocks_env_write():
    h = default_hooks()
    try:
        h.emit("PreToolUse", {"tool_name": "file_write", "path": ".env", "input": ""})
        raise AssertionError("should have blocked")
    except HookDenied:
        print("ok hook blocks .env write")


def test_registry_has_new_tools():
    names = {t.name for t in tool_registry.list_tools()}
    for n in ("file_read", "file_write", "file_list", "python_exec", "bash_exec", "web_search", "web_fetch"):
        assert n in names, f"missing {n}"
    print("ok registry:", sorted(names))


async def _async_tests():
    ex = GuardedExecutor(audit=AuditLog("/tmp/m0_audit.jsonl"))
    r = await ex.run("bash_exec", {"command": "echo m0-ok"})
    assert r.success and "m0-ok" in r.content, r
    print("ok guarded bash_exec")
    r = await ex.run("bash_exec", {"command": "rm -rf /"})
    assert not r.success and "hook" in (r.error or "").lower(), r
    print("ok guarded blocks dangerous")
    r = await ex.run("file_write", {"path": ".env", "content": "x"})
    assert not r.success, r
    print("ok guarded blocks .env")
    r = await ex.run("python_exec", {"code": "print(40 + 2)"})
    assert r.success and "42" in r.content, r
    print("ok guarded python_exec single-run:", r.content.strip().splitlines()[-1])


if __name__ == "__main__":
    test_permission_last_match_wins()
    test_permission_shell_prefix()
    test_default_policy_blocks_env()
    test_hook_blocks_dangerous_shell()
    test_hook_blocks_env_write()
    test_registry_has_new_tools()
    asyncio.run(_async_tests())
    print("\nM0 kernel: all green")
