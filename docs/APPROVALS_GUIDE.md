# ✅ Approvals User Guide — راهنمای تاییدیه‌ها

> Every sensitive agent action pauses for YOUR permission. Nothing runs while pending.
> هر اقدام حساس ایجنت برای اجازه **شما** متوقف می‌شود. تا تایید نکنید هیچ چیزی اجرا نمی‌شود.

---

## EN — How it works

1. The agent wants to do something beyond chatting (run a terminal command, write a file, control the browser).
2. The OS checks policy + risk score and **pauses** the action.
3. A card appears in the **Approvals tab** with:
   - **What is this?** — plain-language explanation of the command (what it does, reversible or not).
   - **Agent's reason** — why the agent wants to do it, in its own words.
   - **Risk badge** — LOW (green) / MEDIUM (yellow) / HIGH (orange) / CRITICAL (red).
   - **Raw details** — the exact command/arguments (for experts).
   - **Expiry time** — if you do nothing, the request expires by itself. Safe default.
4. You press **Approve** (runs it) or **Reject** (blocks it, the agent is told why).
5. Everything is written to the audit log, win or lose.

### Example for beginners: terminal command

You see: `Run this command: npm install lodash`
- **What is this?** → "Downloads packages from the internet and runs install scripts."
- **Reversible?** → No — installed software stays until removed.
- **Risk** → MEDIUM/HIGH. Ask yourself: *did I ask the agent to install something? Do I trust this package name?*
- Rule of thumb: if you don't understand the command, press **Reject** and ask the agent to explain in chat first.

### Risk levels cheat-sheet

| Badge | Meaning | What to do |
|---|---|---|
| LOW | Read-only (read file, list folder, web search) | Usually safe to approve |
| MEDIUM | Writes files in your workspace | Approve if you asked for this change |
| HIGH | Runs terminal commands, network, publishes | Read the explanation box carefully first |
| CRITICAL | Deletes data / touches secrets / remote-code pipes | **Auto-blocked** — you won't even see approve; this is intentional |

### Expiry & safety nets

- Unanswered requests **expire automatically** (default 10 min, then hourly sweep).
- A timed-out or rejected action **never executes** — the agent receives the refusal as feedback.
- `rm -rf /`, secret files (`.env`, keys), and `curl … | sh` shapes are **denied by the OS itself**, no human needed.

---

## FA — راهنمای فارسی

۱. هر وقت ایجنت بخواهد کاری فراتر از چت بکند (اجرای دستور ترمینال، نوشتن فایل، کنترل مرورگر)، سیستم **اجرا را متوقف** می‌کند.
۲. کارتی در **تب تأییدها** می‌آید شامل:
   - **این چیست؟** — توضیح ساده دستور (چه می‌کند، برگشت‌پذیر است یا نه).
   - **دلیل ایجنت** — خودش می‌گوید چرا می‌خواهد این کار را بکند.
   - **نشان ریسک** — کم (سبز) / متوسط (زرد) / زیاد (نارنجی) / بحرانی (قرمز).
   - **جزئیات فنی** — دستور دقیق (برای حرفه‌ای‌ها).
   - **انقضا** — اگر کاری نکنید، درخواست خودش منقضی می‌شود.
۳. **تایید** یعنی اجرا، **رد** یعنی لغو (و ایجنت دلیلش را می‌فهمد).
۴. همه‌چیز در لاگ حسابرسی ثبت می‌شود.

### مثال برای مبتدی‌ها: دستور ترمینال

می‌بینید: `اجرای این دستور: npm install lodash`
- **این چیست؟** → «دانلود پکیج‌ها از اینترنت و اجرای اسکریپت نصب»
- **برگشت‌پذیر؟** → نه.
- **ریسک** → متوسط/زیاد. از خودتان بپرسید: *آیا من خواستم چیزی نصب شود؟ به این اسم پکیج اعتماد دارم؟*
- قاعده سرانگشتی: اگر دستور را نمی‌فهمید، **رد** کنید و اول در چت از ایجنت توضیح بخواهید.

### جدول ریسک

| نشان | معنی | چه کنید |
|---|---|---|
| کم | فقط خواندن | معمولاً امن است |
| متوسط | نوشتن فایل در فضای کاری | اگر همین تغییر را خواستید تایید کنید |
| زیاد | اجرای ترمینال، شبکه، انتشار | اول کادر توضیح را کامل بخوانید |
| بحرانی | حذف داده / دست‌زدن به کلیدها | **خودکار مسدود می‌شود** — عمداً دکمه تایید ندارد |

### تورهای ایمنی

- درخواست‌های بی‌پاسخ **خودکار منقضی** می‌شوند.
- اقدام ردشده یا منقضی‌شده **هرگز اجرا نمی‌شود**.
- الگوهای مخرب (`rm -rf /`، فایل‌های `.env`/کلید، `curl … | sh`) توسط خود سیستم مسدودند.

---

## For operators (both languages / دوزبانه مختصر)

- Policy file: `PermissionEngine` rules in `security/permissions.py` (allow/ask/deny, last-match-wins).
- Auto-approve is **OFF** on the gated path (`run_gated`); legacy `run()` unchanged for backward compat.
- Agent opt-in: `ReActAgent._act(..., require_approval=True, purpose="...", lang="fa")`.
- Housekeeping: `POST /api/v1/approvals/sweep-expired` (safe to cron).
- Test checklist: **T16** in `docs/PENDING_TESTS.md`.
