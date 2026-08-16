# MAGoCo-Self-Evo Architecture & Blueprint

> **Multi-Agent Go-Coordinator with Self-Evolution & Multi-Interface Platform**
> پلتفرم جامع هوش مصنوعی چندایجنتی، خودتکاملی، ابزارمحور، با پشتیبانی از وب‌سایت، کدینگ IDE، اتوماسیون و اتصال به شبکه‌های اجتماعی (تلگرام و...).

---

## 🏗️ ۱. ساختار کلان ماژولار (Monorepo)

پروژه به صورت کاملاً ماژولار طراحی شده تا افزودن ویژگی‌های جدید نیازی به بازنویسی کدهای قبلی نداشته باشد:

```
MAGoCo-Self-Evo/
├── apps/
│   ├── backend/               # FastAPI + WebSocket + Celery Worker
│   ├── frontend/              # Vite + React + Tailwind + Shadcn/ui (Chat + IDE + Settings + Workflow)
│   └── gradio-ui/             # Gradio lightweight alternative UI
├── gateways/                  # پل‌های ارتباطی خارجی
│   ├── telegram/              # ربات تلگرام دوطرفه (متن، وویس، تاپیک‌ها)
│   └── webhooks/              # وب‌هوک‌های عمومی و ایونت‌ها
└── packages/
    ├── magoco-core/           # هسته مرکزی ایجنت‌ها، حافظه، ابزارها و ReAct Loop
    └── magoco-workflows/      # موتور اجرای گراف‌ها و تسک‌های زمان‌بندی (Cron/Event)
```

---

## 🎨 ۲. قابلیت‌ها و ماژول‌های کلیدی (Features)

### الف) لایه ارتباطی و رابط‌های کاربری (Interfaces)
- **چت و کنسول ایجنت (Chat & Agent Console):**
  - استریمینگ زنده پاسخ‌ها + بلوک‌های تفکر (Thinking/Reasoning)
  - کارت‌های تعاملی ابزارها با قابلیت تایید دستی (Human-in-the-loop Approval)
- **حالت کدینگ (Coding Mode / Web IDE - الهام از QwenPaw):**
  - پنل سه‌گانه (درخت فایل، ویرایشگر کد با Diff Preview، و چت با ایجنت برنامه‌نویس)
- **داشبورد تنظیمات (Settings Dashboard):**
  - مدیریت ارائه‌دهندگان مدل (OpenAI, Anthropic, Ollama, HuggingFace و...)
  - مدیریت مهارت‌ها (`SKILL.md` پویای الهام‌گرفته از Hermes)
  - مدیریت حافظه و دسترسی‌ها
- **سازنده گراف جریان‌کاری (Visual Workflow Designer - الهام از Dify/LangFlow):**
  - ساخت اتوماسیون‌ها به صورت Drag & Drop

### ب) کانال‌های ارتباطی بیرونی (Gateways)
- **تلگرام:** اتصال دوطرفه کامل (ارسال پیام، مدیریت گروه‌ها و تاپیک‌ها، تبدیل صوت به متن و بالعکس).
- **وب‌هوک:** قابلیت اتصال به پلتفرم‌های دیگر (n8n، گیت‌هاب و...).

### ج) هسته ایجنت و امنیت (Core & Security)
- **سیستم حافظه ۳ لایه (الهام از QwenPaw):** Working Context + Full Verbatim History + Distilled Knowledge
- **سیستم ابزارها و Sandbox:** اجرای امن کدها در محیط ایزوله و محافظت‌شده (Tool/File Guard)
- **خودتکاملی (Self-Evolution):** بازخوردگیری خودکار و بهینه‌سازی پرامپت‌ها و مهارت‌ها به مرور زمان.

---

## 🗺️ ۳. نقشه راه فازبندی توسعه (Roadmap)

- **فاز ۱:** تکمیل `magoco-core` (ابزارها، Sandbox، حافظه ۳ لایه، ری‌اکت لوپ)
- **فاز ۲:** تکمیل `backend` و ایجاد APIهای WebSocket و احراز هویت
- **فاز ۳:** پیاده‌سازی `frontend` شامل پنل چت، Web IDE و داشبورد تنظیمات
- **فاز ۴:** راه‌اندازی `gateway` تلگرام و سیستم اتوماسیون زمان‌بندی‌شده
- **فاز ۵:** استقرار نهایی، تست‌های یکپارچه و بهینه‌سازی Docker
