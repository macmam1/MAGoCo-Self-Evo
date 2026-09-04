# CLAUDE.md — Project-Specific Conventions for MAGoCo-Self-Evo

## Stack

- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS
- **Backend**: Python 3.11 + FastAPI + SQLModel + LanceDB + SQLite
- **LLM Providers**: OpenAI (GPT-4o/o1), Anthropic (Claude 3.5 Sonnet/Opus), Google (Gemini 1.5), Ollama (local), DeepSeek
- **Browser Automation**: Playwright (headless Chromium) via FastAPI wrapper
- **State Management**: Redux Toolkit (or Zustand) + WebSocket sessions
- **Deployment**: Docker + Docker Compose + Railway/Render one-click

## Directory Map (critical paths)

```
apps/frontend/          # React UI — never edit paths under packages/magoco-core/
  src/
    components/         # UI components — TopBar, Sidebar, ChatConsole, etc.
    layout/             # Layout components — Shell, CommandPalette, CommandCenter
    i18n.ts             # fa/en languages + RTL toggle + dir="rtl"/"ltr"
    theme/              # theme.ts — 5 themes × system/auto, 3 fonts, 2 densities
    lib/                # utilities (ws, api client, localStorage preferences)
    config.ts           # API_URL, WS_URL from .env
  public/               # static assets

packages/magoco-core/   # Core security + agent engine — STABLE API
  src/
    security/           # PermissionEngine, HookEngine, GuardedExecutor, audit.py
    tools/              # 7 tools: bash_exec, file_read, file_write, file_list, python_exec, web_search, web_fetch
    agents/             # ReActAgent, tool registry, skill system
    hooks.py            # 10 lifecycle events with callable/command handlers + guards
    permissions.py      # allow/ask/deny, last-match-wins, .env blocking defaults
    executor.py         # GuardedExecutor wrapping all tool calls + JSONL audit
  tests/                # unit + integration tests

config.ts               # MUST match .env values — never hardcode API_URL/WS_URL
```

## Operational Invariants (2026-09 incident log)

1. **One memory store, anchored**: Never `lancedb.connect()` a CWD-relative path.
   Route through `LanceDBHandler._resolve_local_db_path`. Startup auto-adopts
   legacy root stores; keep new store access on that handler.

2. **The API server does NOT run `--reload`**. After editing backend code run
   `backend/scripts/restart_backend.sh` and only then reproduce/verify.

3. **i18n state consistency**: The `fa/en` language toggle + RTL state must be
   consistent between `useThemePreferences()` in `i18n.ts` and the `<html dir>`
   attribute. Mismatch causes Sidebar collapse or TopBar search disappearance.

4. **Theme persistence**: Font (sans/serif/mono), density (default/compact), and
   theme (fusion/midnight/linear/light/system) are persisted to `localStorage`
   under key `magoco-prefs`. On fresh start, `applyAllPreferences()` reads them.

5. **Tool call audit**: Every tool call (bash_exec, file_write, python_exec,
   web_search, web_fetch) is recorded in `logs/audit.jsonl` via
   `GuardedExecutor.audit_log()`. Never drop tool errors — record them as
   metadata, never silently swallow.

6. **Permission policy**: The PermissionEngine uses last-match-wins ordering.
   `.env` file writes are denied by default (blocked at policy compile time).
   Always check `policy.check("write", ".env")` before attempting file edits.

7. **Hook engine guards**: The HookEngine has 10 lifecycle events. Built-in guards
   block: `rm -rf /`, fork-bomb (`(;(){}|);`), `curl|sh`, `.env` writes.
   If you add a new hook handler, you MUST register a guard or the handler will
   be auto-rejected on `hook_engine.run("init")`.

8. **WS session isolation**: Each browser agent session gets its own WebSocket
   room. Do not share WS rooms between different user sessions — data leakage
   risk. Use `ws_manager.join_room(session_id)` and `ws_manager.leave_room()`.

9. **Frontend → Backend API**: All API calls go through `config.ts` endpoints.
   Never hardcode `http://localhost:8000` — use `import { API_URL } from '../config'`.

10. **Browser preview is screenshot-streaming only**: The Agent Browser tab
    renders pages via Playwright screenshot frames via WebSocket. No iframe
    embedding (X-Frame-Options blocks >95% of sites). Clicks in the UI are
    forwarded to the agent as coordinates; the agent executes them via
    Playwright. User watches the screenshot update.

---

## Decision Standards (read before any fix/design)

Full version: `docs/AGENTS.md`. The short form:

1. **Whole-repo context, not narrow fixes.** Trace callers/consumers of what you
   touch; check for an existing general mechanism (7 tools, 10 hooks, GuardedExecutor,
   PermissionEngine — never hardcode a ONE-tool special case where the general
   layer applies); check known cross-cutting bug classes (path anchoring, i18n drift,
   WS room isolation, theme persistence); read `git log` + `notes/AGENT_COORDINATION.md`
   so you don't undo another agent's deliberate change.

2. **Evidence over plausibility.** Diagnose from logs, captured payloads (intercept
   the real call), and live reproduction; verify end-to-end at the boundary the
   user touches, including across app restarts when persistence is involved;
   benchmark instead of guessing when comparing options; unit-test any heuristic
   you add.

3. **Research established practice for architectural decisions.** Web-search how
   mature harnesses solve it and cite findings in the commit/PR. Prefer patterns
   with production adoption (Playwright browser streaming, GuardedExecutor pattern,
   last-match-wins policy engine) over bespoke cleverness.

4. **Leave a trail.** Commits explain root cause + evidence + verified-how, scoped
   to your files only; update the coordination doc; flag behavior changes affecting
   other callers.

---

## Never Commit These (per AGENTS.md ⚠️)

| File/Directory | Risk |
|---|---|
| `.env*`, `secrets.json`, `credentials.json`, `*.pem`, `*.key` | Key exposure |
| `logs/audit.jsonl` raw — always redact API keys/tokens before commit |
| `docs/FEATURES.md` in one massive commit — split into per-category PRs |

**Before committing**: `git status` and verify none of the above are staged.