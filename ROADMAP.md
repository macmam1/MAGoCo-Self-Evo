# 🗺️ MAGoCo-Self-Evo — Unified UI Roadmap v2 (Single Interface, ALL features)

> Branch: `feat/v2-unified-ui` | Goal: **every feature of all repos + OpenCode + Claude Code in ONE UI shell.**
> Task list lives in GitHub: **Issues #1–#12 + Milestones M0–M4**. This file mirrors it.

## Milestones

| Milestone | Scope | Issues |
|---|---|---|
| M0 - Kernel & Security | Permission Engine + Hooks + ToolRegistry + MCP + LSP + Sandbox | #1, #2, #3 |
| M1 - Unified Chat + IDE | Shell + streaming chat + Monaco IDE + skills/sessions + marketplace | #4, #5 |
| M2 - Teams + Auto-Builder | Team Playground + MetaGPT SOP + CrewAI NL→flow + task tree | #6, #7 |
| M3 - Knowledge + Integrations | Dify KB + 1000 connectors + Supabase auto-provision + browser IDE + Telegram | #8, #9, #10 |
| M4 - Evolution + Release | Self-evolution + OTel + Docker prod + CI + v1.0 | #11, #12 |

## Epics (check Issues for full checklists)

- [ ] #1 [EPIC-01] Single UI Shell — 12 modules (Dashboard/Chat/IDE/Workflow/Playground/Auto-Builder/Knowledge/Skills/Agents/Approvals/Integrations/Executions/Settings)
- [ ] #2 [EPIC-02] Permission + Hooks Engine (allow/ask/deny + 29 hook events)
- [ ] #3 [EPIC-03] Tools + MCP + LSP (all OpenCode + Claude tools, MCP github/postgres/playwright, LSP diagnostics, sandbox)
- [ ] #4 [EPIC-04] Skills + Subagents + Sessions (SKILL.md, isolated subagents, multi-session, undo/redo/share/fork/compact, AGENTS.md)
- [ ] #5 [EPIC-05] Plugins + Marketplace (bundle install, marketplace.json, versioning)
- [ ] #6 [EPIC-06] Team Playground (Builder + live stream + Gallery + profiler)
- [ ] #7 [EPIC-07] Auto-Builder (SOP pipeline + 3 node types + Supabase flow + task tree)
- [ ] #8 [EPIC-08] Knowledge RAG (KB, Workflow/Chatflow, Human-Input, publish lifecycle)
- [ ] #9 [EPIC-09] Browser IDE (preview, npm-via-chat, Figma import, shadcn gen, Visual Edit)
- [ ] #10 [EPIC-10] Chat-OS + Gateway (Artifacts, Functions, SSO, voice, Telegram duplex, embed widget)
- [ ] #11 [EPIC-11] Self-Evolution (reflection → skill gen → auto-patch + eval)
- [ ] #12 [EPIC-12] Production (OTel, Docker, CI, secrets audit, v1.0 tag)

## Source repos merged (no feature dropped)

Original 16: MetaGPT, OpenHands, Atom, Kilocode, Langflow, n8n, Chatbox, ClawX, Quests, RuFloUI, Pan-UI, AionUi, Open-Design, Hermes Agent/WebUI/Desktop, QwenPaw/AgentScope.
New 8: Dify, Flowise, Langflow-LangGraph, AutoGen Studio, CrewAI Studio, Bolt.new, v0, Lovable, Open WebUI/LobeChat.
Plus: **OpenCode (all tools/permissions/MCP/LSP/skills/sessions)** + **Claude Code (CLAUDE.md/skills/subagents/29 hooks/MCP/plugins/teams/workflows/permissions)**.

## License notes

- Langflow = MIT (safe base for resale). Dify multi-tenant SaaS needs vendor approval. Flowise enterprise modules are commercial. Keep governance code isolated.

## How to work

1. Pick an Epic issue, create `feat/epic-XX-short-name` from `feat/v2-unified-ui`.
2. Implement backend + UI + docs, check boxes in the Issue.
3. PR → review → merge. Close Epic only when all boxes + demo pass.
