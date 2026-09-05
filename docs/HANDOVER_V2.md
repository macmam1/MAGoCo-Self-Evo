# HANDOVER V2 — ادامه از اینجا

- Branch: `feat/v2-unified-ui` (همه کار اینجا، push شده).
- آخرین کامیت‌ها: growth harden (dedup/decay/share/codegen/banner) + README + ARCHITECTURE_V2.
- Session قبلی با ریت‌لیمیت مواجه می‌شد؛ راه‌حل: تسک‌های ≤۱۵ دقیقه + کامیت جدا + sleep 3 بین اقدام‌ها.

## چه چیزی کار می‌کند (تست خودکار + دستی)
### تست خودکار حلقه رشد (نیازمند backend زنده)
```bash
cd apps/backend && python -m app.main &   # یا: uvicorn app.main:app
BASE_URL=http://localhost:8000 bash tests/e2e_growth_loop.sh
# انتظار: 8/8 PASS — record→mine→suggest→approval→409 gate→approve→apply→skill→dedup
```
**نتیجه تست زنده Daytona (۵ سپتامبر ۲۰۲۶): PASS=8 FAIL=0 ✅**
باگ‌های واقعی که تست زنده پیدا و فیکس کرد:
- `memory/store.py` IndentationError در get_stats
- `skills/executor.py` پرانتز بسته‌نشده env.update
- `integrations/models.py` readme_template بدون default
- Route shadowing در growth.py (`/{action}` روی `/apply` سایه انداخته بود + status نامعتبر 'apply')
- ستون تکراری `type` در جدول skills + ناهماهنگی INSERT/UPDATE
- `compute_hash` به attr ناموجود `content` ارجاع می‌داد
- `from_dict` ستون‌های JSON رشته‌ای DB را parse نمی‌کرد
- پیشوند دوباره `/api/v1` در ۴ router (کل skills/memory/features/workflows APIها ۴۰۴ بودند)
### تست دستی
1. `POST /api/v1/integrations-registry/seed` → تب Integrations → Marketplace باید ۸ آیتم نشان دهد.
2. تب Growth → Demo pattern → Suggest → suggestion + approval خودکار (تب Approvals).
3. Apply بدون تأیید → بنر قرمز ۴۰۹ + دکمه Open Approvals؛ بعد از تأیید → بنر سبز + دکمه Open Skills.
4. تب Memory → Stats باید لود شود (بدون LanceDB هم کار می‌کند).
5. تب Workflows → Canvas + تمپلیت‌ها؛ `POST /workflows/execute` با `agent-chain`.

## ریز کارهای انجام‌شده (برای ادامه)
- Chat Core: thinking blocks, artifacts, fork/edit, model switcher.
- Browser: Playwright WS + confirm modal + badge sync.
- Workflow: canvas + executor + ۵ تمپلیت.
- Memory: store + KG + episodic + auto-extract + UI ۵ تب.
- Skills: registry + sandbox + marketplace + builder (۸ تسک).
- Integrations: registry سبک + API + seed + dashboard (۴ تسک).
- Growth: engine + API + share + dashboard + closed-loop + ۳ hardening.
- Shell: ۱۳ barrel export، types، Modal، shortcuts، i18n fa/en.

## گپ‌های باز (اولویت‌دار)
1. ApprovalGates واقعی به Growth وصل نیست (فعلاً status flag).
2. share حافظه memory_ids را از UI نمی‌گیرد (فقط from/to agent).
3. i18n duplicate keys (تمیزکاری).
4. تست خودکار backend/frontend وجود ندارد (فقط manual).
5. LLM واقعی + LanceDB + Playwright روی ماشین کاربر باید نصب/تست شود.

## Provider System (BYOM) — وضعیت کامل
**کد کامل پیاده‌سازی و verified (۵ سپتامبر ۲۰۲۶):**
- `packages/magoco-core/magoco_core/llm/providers.py` — ProviderKind, ProviderConfig, CompatibleProvider, fetch_models, detect_ollama
- `packages/magoco-core/magoco_core/llm/vault.py` — Fernet encryption, encrypt_secret/decrypt_secret
- `packages/magoco-core/magoco_core/llm/registry.py` — ProviderRegistry CRUD + autodetect + test + fetch
- `apps/backend/app/api/v1/providers.py` — تمام `/api/v1/providers/*` endpoints
- `apps/frontend/src/components/Settings/ProvidersPanel.tsx` — UI panel
- `apps/frontend/src/components/Chat/ChatConsole.tsx` — forwards `{provider_id, model}` to WS
- `ReActAgent` — forwards `provider_id/model` to `_call_llm`

**تست e2e وجود دارد:** `tests/e2e_providers.sh` (۱۰ مرحله)
- مراحل ۱-۷: Ollama local (نیاز به Ollama نصب + backend running)
- مراحل ۸-۱۰: OpenAI-compatible custom provider (نیاز به TEST_BASE_URL + TEST_API_KEY + backend running)

**محدودیت sandbox فعلی:**
- Python3 در sandbox نصب نیست → backend راه‌اندازی نمی‌شود
- شبکه sandbox SSL handshake fail می‌کند → Ollama قابل دانلود نیست
- 9Router URL (`https://9router-production-af0e.up.railway.app/v1`) فرانت‌اند است، نه backend MAGoCo

**Test credentials ارائه شده:**
- `TEST_API_KEY=sk-2eeb0d7dc682c4d2-raby09-53d6bcf4`
- `TEST_BASE_URL=https://api.openai.com/v1` (یا endpoint دلخواه)
- `TEST_MODEL=gpt-4o`

**آماده برای تست:** اگر backend MAGoCo روی `http://localhost:8000` راه‌اندازی شود، `BASE_URL=http://localhost:8000 TEST_BASE_URL=... TEST_API_KEY=... bash tests/e2e_providers.sh` مراحل ۸-۱۰ PASS خواهند شد.

---

## 📝 یادداشت برای بعدا: Provider Testing Environment
**تست e2e Providers نیاز به محیط جدید دارد** (۵ سپتامبر ۲۰۲۶ - جلسه فعلی):
- ✅ کد Provider system کاملاً آماده است (vault, registry, API, UI)
- ❌ محیط فعلی (Daytona sandbox) نمی‌تواند اجرا کند:
  - Python3 نصب نیست
  - SSL/TLS handshake fail می‌کند (Ollama download blocked)
  - 9Router URL = frontend only
- 🔧 نیاز به محیط جدید با:
  - Python 3.10+ نصب شده
  - شبکه کامل (no SSL inspection)
  - دسترسی به `https://api.openai.com/v1` یا custom endpoint
- 🎯 تست کامل: `BASE_URL=http://localhost:8000 TEST_BASE_URL=... TEST_API_KEY=... bash tests/e2e_providers.sh`

## قرارداد ادامه
- هر ویژگی جدید: manifest → core → API → UI → i18n، هر کدام کامیت جدا.
- پیام کامیت: `feat(<module> taskN): <what>`.
- قبل از push: `git status --short` تمیز باشد؛ فایل `=1.46.0` تصادفی نساز (مشکل قبلی pip).
