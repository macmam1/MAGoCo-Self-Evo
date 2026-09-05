# MAGoCo-Self-Evo — AI OS

> **An agentic operating system that unifies the best features of dozens of open-source AI projects into one modular platform — chat, agents, browser, workflows, memory, skills, integrations, and self-improvement (growth).**

---

## 🧭 Vision & Principles

1. **We are building a framework/OS, not a product with a built-in model.** The app ships with **no model and no API keys**. The user brings their own:
   - **Local models** — Ollama / LM Studio / llama.cpp (auto-detected, pulled from UI), or
   - **Custom providers** — any OpenAI-compatible endpoint: user enters `base_url + api_key + model` in **Settings → Providers** (keys encrypted in DB, never in git/env).
2. **Key-aggregator gateways (9Router, OpenRouter, LiteLLM, Portkey) are NOT providers.** They are just OpenAI-compatible endpoints the user *may* point a custom provider at. No provider-specific code for them — ever. (A past agent wrongly hardcoded `9ROUTER` as a provider; that concept is deleted.)
3. **Don't reinvent — learn from the best.** Before building any feature, study how the top projects solved it (their docs, changelogs, and recorded mistakes). Reference table below. Every new module must cite its references in the commit/PR.
4. **Modular from day one.** Every feature = folder + `manifest.json` + core + API + UI + i18n. Small incremental commits. See `docs/ARCHITECTURE_V2.md` for the binding contract.

## 📚 Reference projects we learn from (not copy-paste)

| Area | Projects studied | What we adopted |
|---|---|---|
| Chat UI providers/BYOM | Open WebUI, LibreChat, LobeChat, AnythingLLM, Jan, Big-AGI | OpenAI-compat `base_url+key+model` as the *only* generic type; `/models` fetch + manual fallback; encrypted DB keys; per-chat model override |
| Agent frameworks | Dify, Flowise, Langflow, CrewAI, MetaGPT | Typed model roles, per-node model choice, load-balancing/fallback |
| Coding agents | Continue, Cline, Aider, OpenCode, Claude Code | Secret/config separation, Plan vs Act modes, small/weak model for cheap jobs |
| Gateways & local runtimes | LiteLLM, Ollama, LocalAI, LM Studio, vLLM, OpenRouter, Portkey, 9Router | Everything is OpenAI-compatible — our consumer needs exactly one client shape |
| Browser agents | browser-use, Skyvern, Stagehand, Anthropic computer-use | Screenshot streaming (not iframes), human-in-the-loop approve |
| Workflow | n8n, Temporal concepts, LangGraph | Visual DAG + conditional/parallel + retry + templates |
| Memory/RAG | MemGPT/Letta, Mem0, GraphRAG | Layered memory (working/semantic/episodic/KG) + white-box editing |
| Governance | rush86999/atom (AGENTS.md/CLAUDE.md pattern) | Whole-repo context, evidence over plausibility, navigable trail |

Full 120-feature inventory: `docs/FEATURES.md`.

---

## ⚡️ Project status (branch `feat/v2-unified-ui` — this is where all work happens)

Legend: ✅ = verified live on real backend · 🟡 = implemented, not yet live-tested · ❌ = mock · 📋 = roadmap.

| Module | Status | Notes |
|---|---|---|
| Backend boot + health | ✅ | Proven on Daytona (Python 3.14, SQLite); needs `PYTHONPATH` (see quickstart) |
| Agent Growth (closed loop) | ✅ e2e 8/8 | Auto-track → mine → suggest → approval → Apply→draft skill; dedup + 409 gate verified live |
| Chat Core | 🟡 | Artifacts, fork/edit, model switcher, fa/en + RTL real; **thinking stream is currently simulated** (real token streaming pending) |
| Provider System (BYOM) | 🔨 In progress | Backend done (vault, registry, API, ReActAgent wiring); Settings UI done; live test pending |
| Agent Browser | 🟡 | Playwright service + WS + confirm modals implemented; **not covered by e2e yet** |
| Workflow Engine | 🟡 | Canvas DAG + executor + 5 templates implemented; execution API not live-tested |
| Memory System | 🟡 | Store + search + KG + episodic + RAG UI implemented; only stats/search touched live |
| Skills System | 🟡 | Registry + sandbox + marketplace + builder implemented; execute path not live-tested |
| Integrations | 🟡 | Registry + seed + dashboard implemented; OAuth flows not live-tested |
| Approvals (HITL) | ✅ | Persistent SQLite + API; verified live via growth e2e (approve/resolve/409) |
| Feature Registry | 🟡 | Manifest + API implemented; not live-tested |
| UI Shell | ✅ | Renders; barrel exports, themes, ⌘K, shortcuts, Modal (visual, no backend needed) |
| Vibe-Coding IDE | ❌ Mock | Tab renders, zero backend calls — file/exec/vibe endpoints pending |
| Command Center / History stats | ❌ Mock | Static numbers — wire to existing stats APIs (small task) |
| Multi-agent teams / Auto-builder | 📋 Roadmap | See open EPIC issues (M2) |

Live e2e scope (Daytona, Sept 2026): growth loop only — `BASE_URL=... bash tests/e2e_growth_loop.sh` → **8/8 PASS**. It found and fixed 8 real backend bugs. Other modules await their own e2e.

---

## 🏗️ Structure

```
MAGoCo-Self-Evo/
├── apps/
│   ├── backend/app/           # FastAPI + WebSockets (/ws/chat, /ws/browser) + REST /api/v1/*
│   ├── frontend/src/          # React + TS + Tailwind; components/<Feature>/ each with index.ts
│   └── gradio-ui/             # ⚠️ legacy parallel UI — DEPRECATED, do not extend
├── packages/
│   ├── magoco-core/magoco_core/  # agents, tools, security, llm, memory, skills, integrations, growth, features
│   ├── magoco-workflows/      # (lightweight; main DAG engine lives in backend services)
│   └── shared/types/          # cross-package TS types (feature-manifest, …)
├── features/*/manifest.json   # one manifest per feature (chat-core, browser-agent, …)
├── docs/                      # HANDOVER_V2, ARCHITECTURE_V2, AGENTS, FEATURES (start here)
├── tests/e2e_growth_loop.sh   # live growth-loop test (needs running backend)
```

**To add a feature:** manifest → core → API (register in `main.py`, single-level prefix!) → UI (`index.ts` + tab in `App.tsx` + `i18n.ts` en+fa) → commit per step. Full contract: `docs/ARCHITECTURE_V2.md`.

---

## 🚀 Quickstart (developer)

```bash
git clone -b feat/v2-unified-ui https://github.com/macmam1/MAGoCo-Self-Evo.git
cd MAGoCo-Self-Evo

# Backend (needs Python 3.11+)
cd apps/backend
pip install fastapi 'uvicorn[standard]' pydantic pydantic-settings sqlalchemy aiosqlite httpx \
  'passlib[bcrypt]' 'python-jose[cryptography]' email-validator python-multipart structlog tenacity pyjwt semver playwright cryptography
pip install -e ../../packages/magoco-core --no-deps
python -m playwright install chromium   # only for Agent Browser
PYTHONPATH=../../packages/magoco-core:../../packages/magoco-workflows:. \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/health

# Frontend
cd apps/frontend && npm install && npm run dev   # http://localhost:5173
```

**First run:** open the app → **Settings → Providers** → add Ollama (local) or a custom OpenAI-compatible provider (`base_url + api_key + model`) → Test Connection → chat. No keys in `.env`, ever.

---

## 🤖 Instructions for AI agents working here (read first!)

1. Read in order: `docs/HANDOVER_V2.md` → `docs/ARCHITECTURE_V2.md` → `docs/AGENTS.md` → `docs/FEATURES.md`.
2. Work only on branch `feat/v2-unified-ui`. Small tasks (≤15 min), one commit each: `feat(<module> taskN): <what>`.
3. **Never commit secrets** (`.env*`, `*.pem`, keys, `auth.json`, `audit.jsonl` raw). Push-protection is on — a blocked push means you staged something bad.
4. Verify with the live backend when touching it (`tests/e2e_growth_loop.sh`); this sandbox has no Python — use Daytona or the user's machine.
5. Outdated docs from early agents (`PROJECT_STATUS_LOG.md`, `architecture.md`, `FEATURE_INTEGRATION_BLUEPRINT.md`) may contradict this README — **this README + `HANDOVER_V2.md` win**. Known stale claims: 9Router-as-provider, ReactFlow designer, YAML-frontmatter skills, `.env` LLM keys.

## 📚 Docs

- [Handover + verification checklist](docs/HANDOVER_V2.md) ⭐ start here
- [Architecture + feature contract](docs/ARCHITECTURE_V2.md)
- [Agent working standards](docs/AGENTS.md) · [Project conventions](docs/CLAUDE.md)
- [120-feature inventory from 30+ platforms](docs/FEATURES.md)

## 📄 License

MIT — see `LICENSE`. (Commercial licensing model, e.g. Business Source, to be decided before monetization.)
