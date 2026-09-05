# HANDOVER V2 — ادامه از اینجا

- Branch: `feat/v2-unified-ui` (همه کار اینجا، push شده).
- آخرین کامیت‌ها: growth harden (dedup/decay/share/codegen/banner) + README + ARCHITECTURE_V2.
- Session قبلی با ریت‌لیمیت مواجه می‌شد؛ راه‌حل: تسک‌های ≤۱۵ دقیقه + کامیت جدا + sleep 3 بین اقدام‌ها.

## چه چیزی کار می‌کند (تست دستی لازم)
1. `POST /api/v1/integrations-registry/seed` → سپس تب Integrations → Marketplace باید ۸ آیتم نشان دهد.
2. تب Growth → Demo pattern → Suggest → باید suggestion بسازد (دفعه دوم نباید duplicate بسازد).
3. Apply → باید بنر سبز + draft skill در تب Skills (status draft) بسازد.
4. تب Memory → Stats باید لود شود (بدون LanceDB هم باید کار کند).
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

## قرارداد ادامه
- هر ویژگی جدید: manifest → core → API → UI → i18n، هر کدام کامیت جدا.
- پیام کامیت: `feat(<module> taskN): <what>`.
- قبل از push: `git status --short` تمیز باشد؛ فایل `=1.46.0` تصادفی نساز (مشکل قبلی pip).
