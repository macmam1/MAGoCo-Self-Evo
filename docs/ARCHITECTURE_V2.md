# ARCHITECTURE V2 — AI OS Modular (feat/v2-unified-ui)

## Module map
- `apps/frontend/src/components/{Chat,Browser,Workflow,Memory,Skills,Integrations,Growth,Layout,ui}/` — هر پوشه `index.ts` دارد (barrel export).
- `apps/frontend/src/{types,hooks,config.ts,i18n.ts,theme/}` — تایپ مرکزی، هوک‌ها، کانفیگ، ترجمه، تم.
- `packages/magoco-core/magoco_core/{features,growth,memory,skills,integrations,security,tools,agents}/` — منطق هسته.
- `apps/backend/app/api/v1/{chat,workflows,skills,features,workflow_executions,memory,integrations_registry,growth}.py` — REST.
- `apps/backend/app/services/{browser_service.py,workflow_executor.py,integrations/seed.py}` — سرویس‌ها.
- `features/{chat-core,browser-agent,workflow-engine,memory-system,skills-system,integrations-system,agent-growth}/manifest.json` — ثبت ویژگی.
- `packages/shared/types/feature-manifest.ts` — اسکیمای مشترک.

## Key flows
1. Chat: `ChatConsole --WS /ws/chat--> ReActAgent (+GuardedExecutor) --> streaming thinking + artifacts`.
2. Browser: `AgentBrowser --WS /ws/browser--> Playwright service (screenshot JPEG) ` + confirm Modal + Sidebar badge via localStorage.
3. Workflow: Canvas DAG (`WorkflowBuilder`) --> POST `/workflows/execute` --> `WorkflowExecutor` (parallel/conditional/retry).
4. Memory: `MemoryDashboard` <--> `/api/v1/memory/*` <--> `MemoryStore` (LanceDB vectors + SQLite + JSONL episodic).
5. Skills: `SkillsDashboard/Builder/Marketplace` <--> `/api/v1/skills/*` <--> `SkillsRegistry` + `SandboxExecutor`.
6. Integrations: `IntegrationsDashboard` <--> `/api/v1/integrations-registry/*` <--> `IntegrationsRegistry` + seed.
7. Growth closed-loop: chat/browser/workflow auto-track --> `GrowthEngine.mine_patterns` --> suggestion --> `POST /growth/suggestions/{id}/apply` --> draft skill in SkillsRegistry --> Skills tab.

## Add a new feature (contract)
1. `features/<id>/manifest.json` بساز.
2. مدل/منطق در `packages/magoco-core/magoco_core/<id>/` + `__init__.py`.
3. API در `apps/backend/app/api/v1/<id>.py` + register در `main.py`.
4. UI در `apps/frontend/src/components/<Id>/` + `index.ts` + تب در `App.tsx` + کلیدهای `i18n.ts`.
5. هر مرحله یک کامیت کوچک با پیشوند `feat(<id> taskN):`.

## Run
- Backend needs Python 3.11+: `cd apps/backend && pip install -e . && playwright install chromium && python -m app.main`.
- Frontend: `cd apps/frontend && npm install && npm run dev`.
- Seed integrations: `POST /api/v1/integrations-registry/seed`.
- Growth demo: Growth tab → Demo pattern → Suggest → Apply → Skills tab.

## Notes / gaps
- LLM واقعی (9Router/OpenAI) با کلید واقعی تست نشده.
- LanceDB اختیاری است؛ بدون آن vector search غیرفعال می‌شود.
- Playwright/Chromium در این sandbox نصب نیست؛ روی ماشین کاربر نصب شود.
- i18n ممکن است duplicate key داشته باشد (تمیزکاری بعدی).
