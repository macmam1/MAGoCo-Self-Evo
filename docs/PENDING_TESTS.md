# 🧪 PENDING TESTS — محیط تست در انتظار

> این فایل تنها مرجع «چه چیزی هنوز تست نشده و در چه محیطی باید تست شود» است.
> هر بخش که ساخته می‌شود و نیاز به تست دارد، اینجا ثبت می‌شود تا فراموش نشود.
> وضعیت محیط فعلی: در انتظار تهیه محیط جدید توسط کاربر.

## 1) مشخصات محیط تست

### حداقل (حداقلی — بدون Ollama/Playwright/LanceDB سنگین)
| منبع | حداقل | توضیح |
|---|---|---|
| CPU | **2 vCPU** | بک‌اند FastAPI + فرانت Vite |
| RAM | **4 GB** | بک‌اند ~1GB + بیلد فرانت ~1.5GB + حاشیه OS |
| Disk | **10 GB آزاد** | مخزن 8MB + وابستگی pip ~2-3GB + node_modules ~1GB + دیتای SQLite |
| نرم‌افزار | Python 3.11+، Node 20+، git، curl، bash، sqlite3 | بدون نیاز به مرورگر/مدل محلی |
| شبکه | egress کامل HTTPS (pypi، npm، APIهای سازگار OpenAI) | بدون SSL-inspection که handshake را reset کند |
| تست‌های قابل اجرا در حداقل | growth e2e، memory v2 API، planning، provider steps 8-10 (custom endpoint)، بیلد فرانت | بدون Ollama local و Playwright |

### حداکثری (کامل — همه چیز)
| منبع | حداکثری | توضیح |
|---|---|---|
| CPU | **4 vCPU (ترجیحاً 8)** | اجرای موازی Playwright + Ollama + بک‌اند |
| RAM | **8 GB حداقل، 16 GB پیشنهادی** | مدل 3B حدود 2-4GB + هر سشن Chromium حدود 1GB + LanceDB/embeddings |
| Disk | **25-30 GB آزاد** | مدل Ollama ‏2-5GB + Chromium ‏0.5-1GB + کش pip/npm + وکتورها + رشد دیتا |
| GPU | اختیاری | فقط سرعت Ollama را بالا می‌برد، اجباری نیست |
| نرم‌افزار | حداقل + Playwright Chromium + Ollama + LanceDB | `playwright install chromium` |
| شبکه | حداقل + `api.telegram.org` + `github.com` + registry مدل Ollama | برای تلگرام و دانلود مدل |
| تست‌های قابل اجرا در حداکثری | همه موارد حداقل + provider steps 1-7 (Ollama local) + مرورگر + RAG وکتوری واقعی | پوشش کامل e2e |

### چرا سندباکس قبلی شکست خورد (درس)
- دیسک 3GB → دانلود Ollama و نصب وابستگی‌ها نصف‌کاره ماند.
- نبود Python3/Node در ایمیج پایه + `SSL Connection reset by peer` روی `ollama.com` و `httpbin`.
- نتیجه: فقط بازبینی کد، بدون اجرای بک‌اند.

## 2) لیست تست‌های در انتظار (هر ردیف = یک بخش ساخته‌شده)

| # | بخش | دستور تست | محیط لازم | وضعیت |
|---|---|---|---|---|
| T1 | Provider e2e کامل (10 مرحله) | `BASE_URL=http://localhost:8000 TEST_BASE_URL=https://api.openai.com/v1 TEST_API_KEY=sk-... TEST_MODEL=gpt-4o bash tests/e2e_providers.sh` | حداقل (steps 8-10) / حداکثری (steps 1-7 با Ollama) | ⏳ منتظر محیط |
| T2 | Growth loop e2e (8/8) | `BASE_URL=http://localhost:8000 bash tests/e2e_growth_loop.sh` | حداقل | ⏳ رگرسیون بعد از تغییرات حافظه |
| T3 | Memory v2: core-blocks CRUD + append | `PUT /memory/core-blocks` → `POST /memory/core-blocks/{label}/append` → `GET /memory/core-blocks` | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T4 | Memory v2: supersede + current_only | `POST /memory/supersede` → `POST /memory/search {"current_only": true}` | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T5 | Memory v2: decay + touch | `POST /memory/decay` → `POST /memory/{id}/touch` | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T6 | Memory v2: self-editing tools (8 ابزار) | فراخوانی `core_memory_append`/`archival_memory_search`/`memory_supersede` از طریق ایجنت | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T7 | Planning orchestrated execute | `POST /planning/{id}/execute-orchestrated` + دکمه Execute در UI | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T8 | Telegram gateway | `POST /telegram/test-token` + ثبت بات + `/start` در چت واقعی | حداکثری (دسترسی به api.telegram.org + توکن BotFather) | ⏳ ساخته‌شده، تست‌نشده |
| T9 | Gateway rate-limit + fallback chains | `get_rate_limit_status` / `get_fallback_chains` زیر بار چند پروایدر | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T10 | Frontend build + Planning/Memory/Telegram tabs | `cd apps/frontend && npm install && npm run build` + کلیک تب‌ها | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T11 | Context Guardian: topics/snapshot/scoped recall | `POST /memory/guardian/add` چند پیام دوموضوعی → `GET /memory/guardian/{sid}/scoped` (فقط تاپیک فعال + سامری) → `GET /memory/snapshots/{sid}` | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T12 | Model compensator: weak vs strong preamble | `POST /memory/compensate {"model":"llama3.1:8b",...}` در برابر `{"model":"gpt-4o",...}` (مقایسه طول/صراحت preamble) | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T13 | Escalation + JSON guard + overrides | `POST /memory/escalation/advise {"model":"...","error":"json parse failed",...}` + `task_needs` در compensate | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T14 | Capability gate + deferred queue | `POST /memory/gate-check` با تسک پیچیده روی مدل ضعیف → queued → `GET /memory/deferred` → resolve؛ + تست kill-switch (`enabled=false`) | حداقل | ⏳ ساخته‌شده، تست‌نشده |
| T15 | **سیم‌کشی دروازه به چت زنده (بعداً + با تست کامل)** | فقط بعد از PASS شدن T14: وصل opt-in به WS چت (پیش‌فرض خاموش) → تست پیام ساده (assign) + پیام پیچیده روی مدل ضعیف (defer شفاف) + تست خاموش بودن flag → بعد روشن کردن پیش‌فرض | حداقل | ⏳ عمداً وصل نشده — خطر تغییر رفتار زنده بدون تست |

## 3) قرارداد
- هر فیچر جدید که نیاز به بک‌اند زنده دارد → یک ردیف جدید به جدول بالا اضافه کن.
- بعد از فراهم شدن محیط، از T1 شروع کن (بلوکر بقیه نیست ولی مهم‌ترین است)، سپس T2 (رگرسیون)، بعد T3-T7.
- نتیجه هر تست را همین‌جا با تاریخ و PASS/FAIL ثبت کن.
