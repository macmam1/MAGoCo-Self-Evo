# 🗺️ MAGoCo-Self-Evo: Phase Roadmap

> **ترکیب Multi-Agent Platform + Coding IDE + Multi-Interface Gateway + Self-Evolution**

---

## 📦 Phase 1: Core Engine & Tooling (Priority: P0 — Now)
**هدف:** ساختن پایه‌های ایجنت‌های واقعی و ابزارهای اجرایی.

### تسک‌ها:
- [x] **Discipline: Remove dead deps (`crewai`, `langchain`)** از `pyproject.toml`
- [ ] **Core: Complete `ToolRegistry`** — ساخت ابزارهای `bash_exec`, `file_read`, `file_write`, `web_search`, `code_exec_sandbox`
- [ ] **Core: Implement `ReAct Agent Loop`** — توانایی فکر کردن، تصمیم‌گیری و اجرای ابزار
- [ ] **Core: Add `Security Guard`** — لایه امنیتی برای جلوگیری از اجرای کدهای خطرناک (File/Tool Guard)
- [ ] **Core: `Tool Execution Cards`** — کارت‌های جلوه‌گر برای نمایش ابزار در حال اجرا به کاربر
- [ ] **Docs: Fix broken README links** (`docs/architecture.md` -> این سند)
- [ ] **Git: Remove confusing files** — پوشه‌های `apps/gradio-ui`, `apps/frontend` اضافی و بی‌استفاده (درصورتی که جایگزین نداریم)

---

## 📦 Phase 2: Backend API & WebSocket (Priority: P1)
**هدف:** فعال‌سازی ارتباطات بلادرنگ و APIها.

- [ ] **Backend: `WebSocket` chat endpoint** — `/api/v1/agents/{id}/chat/ws`
- [ ] **Backend: `Streaming` Response** — استریم کانال‌های LLM به صورت زنده (SSE + WebSocket)
- [ ] **Backend: Human-in-the-loop approval** — کارت‌های تأیید ابزار (Tool Approval) از سمت کاربر
- [ ] **Backend: `Agent CRUD`** **API** — ایجاد، ویرایش و حذف ایجنت‌ها از طریق API

---

## 📦 Phase 3: Frontend — UI Dashboard & Chat (Priority: P2)
**هدف:** ظاهر زیبا، ماژولار و کاربردی.

- [ ] **Frontend: `Chat Console`** — پنل چت با استریمینگ زنده، تاریخچه و جابجایی بین ایجنت‌ها
- [ ] **Frontend: `Coding Mode / Web IDE`** — پنل سه‌گانه (فایل‌ها، ویرایشگر، چت و Diff)
- [ ] **Frontend: `Settings Dashboard`** — صفحه تنظیمات LLM Providers, Skills, Memory
- [ ] **Frontend: `Workflow Designer`** — ویرایشگر گراف تسک‌ها (Drag & Drop)
- [ ] **Frontend: `Multi-Channel Control`** — قابلیت انتخاب کانال خروجی (API / Telegram / Direct)

---

## 📦 Phase 4: Gateways & Automation (Priority: P3)
**هدف:** اتصال به شبکه‌های اجتماعی و اتوماسیون.

- [ ] **Telegram Bot: `Gateway für Telegram`** — اتصال دوطرفه کامل
- [ ] **Telegram Bot: `Voice-to-Text` & `Text-to-Voice`** — پشتیبانی از وویس
- [ ] **Scheduler: `Cron jobs system`** — تسک‌های زمان‌بندی‌شده برای ایجنت‌ها
- [ ] **Scheduler: `Event-driven Triggers`** — واکنش به رویدادها

---

## 📦 Phase 5: Production & CI/CD (Priority: Final)
**هدف:** تولید و استقرار.

- [ ] **CI/CD: GitHub Actions** — تست + Lint + Build
- [ ] **Docker: `Optimization`** — Healthchecks, multi-stage builds
- [ ] **Security: Audit** — بازبینی نهایی اسرار و JWT/API Keys