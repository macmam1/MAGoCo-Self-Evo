# MAGoCo-Self-Evo

> **Multi-Agent Go-Coordinator with Self-Evolution & Multi-Interface Platform**
> پلتفرم multi-agent با قابلیت خودتکاملی، کدینگ IDE، چت، داشبورد تنظیمات، اتصال به شبکه‌های اجتماعی (تلگرام) و اتوماسیون.

## 🏗️ ساختار کلان (ماژولار)

این یه **monorepo** کاملاً ماژولار هست:

```
MAGoCo-Self-Evo/
├── apps/
│   ├── backend/               # FastAPI + WebSocket + Celery Worker
│   ├── frontend/              # Vite + React + Tailwind + Shadcn/ui (Chat + IDE + Settings + Workflow)
│   └── gradio-ui/             # Gradio lightweight alternative UI
├── gateways/                  # پل‌های ارتباطی خارجی (Telegram, Webhooks)
└── packages/
    ├── magoco-core/           # هسته مرکزی: Agent + Tools + Memory + ReAct + Security Guard
    └── magoco-workflows/      # موتور اجرای گراف‌ها و تسک‌های زمان‌بندی
```

## 🎨 قابلیت‌ها

- **Chat Console** با استریمینگ زنده + بلوک‌های تفکر ایجنت (Thinking/Reasoning)
- **Coding Mode / Web IDE** سه‌پنلی (فایل، ویرایشگر با Diff Preview، چت با ایجنت برنامه‌نویس)
- **Settings Dashboard** برای LLM Providers, Skills, Memory
- **Visual Workflow Designer** (Drag & Drop - الهام از Dify/LangFlow)
- **Telegram Bot Gateway** (متن، وویس، تاپیک‌ها، Approval inline-buttons)
- **۳-Layer Memory System** + **Self-Evolution Engine** + **Sandbox Security Guard**

## 🚀 شروع سریع (Development)

### پیش‌نیازها
- Docker + docker-compose
- (اختیاری) uv برای backend توسعه محلی
- (اختیاری) pnpm/npm برای frontend توسعه محلی

### نصب و اجرا
```bash
# 1. کپی env
cp .env.example .env

# 2. اجرای همه سرویس‌ها
docker-compose up -d

# 3. بررسی سلامت
curl http://localhost:8000/health
open http://localhost:5173
```

| سرویس | URL | توضیح |
|--------|-----|-------|
| Backend API | http://localhost:8000 | FastAPI |
| API Docs (Swagger) | http://localhost:8000/docs | OpenAPI auto-generated |
| Frontend | http://localhost:5173 | Vite dev server |
| Postgres | localhost:5432 | DB |
| Redis | localhost:6379 | Cache + Queue |
| Gradio UI | http://localhost:7860 | رابط ساده |

## 🛠️ توسعه محلی (بدون Docker)

### Backend
```bash
cd apps/backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend
```bash
cd apps/frontend
pnpm install
pnpm dev
```

## 📐 اصول معماری

- **🎯 ماژولار**: هر feature یه ماژول مستقل با interface واضح
- **🔌 Plugin-based**: agent ها، storage ها، LLM provider ها همه pluggable
- **🚩 Feature flags**: ویژگی‌ها قابل فعال/غیرفعال شدن بدون تغییر کد
- **🏛️ Hexagonal**: business logic از infrastructure جدا
- **📦 Microservice-ready**: هر app مستقل deploy میشه

## 📚 مستندات بیشتر

- [معماری](docs/architecture.md)
- [راه‌اندازی backend](apps/backend/README.md)
- [راه‌اندازی frontend](apps/frontend/README.md)
- [راه‌اندازی Gradio](apps/gradio-ui/README.md)

## 📄 License

MIT
