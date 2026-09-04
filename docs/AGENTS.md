# AGENTS.md — Working Standards for AI Agents in MAGoCo-Self-Evo

Every agent (OpenCode, Claude Code, Qwen Code, or human pairing with one) follows
these decision standards. Project specifics live in `CLAUDE.md`; multi-agent
coordination protocol lives in `notes/AGENT_COORDINATION.md` (local, gitignored).

## 1. Decide with the WHOLE repo in context — no narrow fixes

- **Trace the neighborhood before editing.** Find the callers, the consumers,
  and the parallel implementations of anything you touch. A fix that is correct
  for one call site and silently changes behavior for five others is not a fix.
  (Real case: making `LLMService.generate_completion` pass full message lists
  changed behavior for EVERY caller — flagged and audited, not just the chat path.)
- **Look for the existing general mechanism before adding a special case.**
  This repo has 7 tool registries, 10 lifecycle hooks, and a GuardedExecutor
  wrapping all tool calls. If you're about to hardcode behavior for ONE tool
  (a regex that detects "web" requests, a bash-specific branch), stop: the same
  need almost certainly exists for every other tool. Build or use the general layer
  instead.
- **Check for the known cross-cutting bug classes before assuming local cause:**
  - **Path anchoring**: anything resolving `./data/...` or relative paths must
    be anchored to `apps/frontend/` or `packages/magoco-core/` (root-vs-root
    launches already caused divergent theme preferences, backend URLs, and i18n
    state — most recently when the agent forgot font persistence across restarts).
    Startup reconciliation (`config.ts` + `theme/theme.ts`) now auto-resets to
    `.env` defaults; keep new pref access through those entry points.
  - **Stale server = false bug reports**: the frontend does not auto-reload.
    After frontend code changes, run `npm run dev` and only then reproduce/verify.
  - **Message flattening**: the LLM layer must receive full message lists;
    anything that reduces to (last-prompt, last-system) destroys multi-turn.
  - **i18n state drift**: the `fa/en` language toggle + RTL state must be
    consistent between `useThemePreferences()` and the `<html dir>` attribute.
    Mismatch causes the sidebar to collapse or the TopBar search to disappear.
- **Read the run history.** `git log`, recent commits by other agents, and
  `notes/AGENT_COORDINATION.md` — someone may have already built (or
  deliberately removed) what you're about to add. E.g. the permission
  `deny-on-.env-write` was implemented on purpose (security); don't reintroduce
  it to make a test pass.

## 2. Evidence over plausibility

- **Diagnose from runtime evidence**: logs (`backend/logs/`, `logs/`), captured
  request/response payloads (intercept the actual call — don't reason about what
  "should" be in it), DB rows, and live reproduction. Most of this session's
  worst bugs (theme drift, permission bypass, hook ordering) were invisible until
  the real payload was captured.
- **Verify fixes end-to-end at the boundary the user touches** (the chat input,
  the browser tab, the theme toggle). Include across app restarts when persistence
  is involved.
- **Measure, don't guess, when comparing options**: UI load time, WebSocket
  latency, feature usage — a small benchmark beats an opinion. Keep the numbers
  in the PR/commit message.
- **Unit-test heuristics you add** (permission guards, hook ordering, i18n
  direction toggles) with realistic inputs, and re-run them after changes.

## 3. Research established practice for architectural decisions

- Before designing anything novel (tool selection, memory, routing, agents),
  **web-search how mature harnesses solve it** and cite what you found in the
  commit/PR. Prefer patterns with production adoption (e.g. Playwright-based
  browser streaming as used by Skyvern/Anthropic, not custom iframe hacks).
- When research and repo constraints conflict, say so explicitly and pick with
  reasons — don't silently follow either.

## 4. Leave the trail navigable

- Commit messages explain WHY (root cause, evidence, verified-how), scoped to
  only the files you actually changed — other agents' in-flight work stays
  unstaged.
- Update `notes/AGENT_COORDINATION.md` when you start/finish work on shared
  files, and log incidents (theme drift, policy engine blocks, WS disconnects)
  there.
- Behavior changes that affect other callers must be flagged in the
  coordination doc and the commit message.

---

## ⚠️ NEVER Commit

| File/Directory | Risk |
|---|---|
| `packages/magoco-core/.env*`, `packages/magoco-core/secrets.json`, | Key/credential exposure |
| `apps/frontend/.env*` (if containing API keys) | |
| `logs/*.jsonl` (contains audit trails of tool calls) | Redact secrets before commit |
| `docs/FEATURES.md` (217 lines — massive file) | Prefer splitting into smaller docs per category |

**Before committing**: `git status` and verify none of the above are staged. **If leaked**: rotate keys, `git filter-repo`/BFG (NOT `git rm`), force-push only after history is clean, notify maintainers.

---

## Evolution Maturity Levels

| Level | Confidence | Capabilities | When Agent Auto-Upgrades |
|---|---|---|---|
| **STUDENT** | <0.5 | Read-only: chat, model switching, theme toggles, i18n | Upgrade to INTERN after 5 successful sessions with tool usage |
| **INTERN** | 0.5–0.7 | Streaming: agent tool calls, workflow steps, browser preview, file ops | Upgrade to SUPERVISED after 3 sessions with approval-based tool execution |
| **SUPERVISED** | 0.7–0.9 | State changes: agent-driven workflows, browser interaction, file modifications | Upgrade to AUTONOMOUS after 3 supervised sessions with no policy denials |
| **AUTONOMOUS** | >0.9 | All actions: unrestricted agent growth, skill auto-generation, cross-agent memory | Respect user-defined limits; never exceed user-set confidence threshold |

> **Tier is routing, not security.** Maturity decides what an agent is *normally* allowed
> to do from past clean runs — it does **not** bound blast radius; a prompt-injected
> agent at any tier acts at that tier's full scope. Bounding blast radius requires the
> deterministic sandbox layer (GuardedExecutor with allow/ask/deny, .env blocking,
> HookEngine guards for `rm -rf /`, fork-bomb, `.env` writes).

---

## Governance Flow (always follow in order)

```
User Request
    ↓
AgentContextResolver (determine intent, check maturity level)
    ↓
GovernanceCache (cached permission check, <1ms)
    ↓
AgentGovernanceService (allow/ask/deny based on last-match-win policy + .env blocks)
    ↓
GuardedExecutor (wrap ALL tool calls with deny/ask/hook-deny + JSONL audit)
    ↓
ReActAgent routing (tool → result → LLM → next tool, with checkpoint)
    ↓
Response to User
```

Every tool call MUST pass through `GuardedExecutor` at `packages/magoco-core/magoco_core/security/executor.py`.
The policy engine at `packages/magoco-core/magoco_core/security/permissions.py` uses
last-match-wins with `.env` blocking (any write to `.env` is denied by default).