# MAGoCo-Self-Evo

> **Multi-Agent Go-Coordinator with Self-Evolution & Multi-Interface Platform**
> پلتفرم multi-agent با قابلیت خودتکاملی، کدینگ IDE، چت، داشبورد تنظیمات، اتصال به شبکه‌های اجتماعی (تلگرام) و اتوماسیون.

## 🏗️ ساختار کلان (ماژولار)

این یک **monorepo** کاملاً ماژولار است:

```
MAGoCo-Self-Evo/
├── apps/
│   ├── backend/               # FastAPI + WebSocket + REST API
│   ├── frontend/              # Vite + React + Tailwind + Shadcn/ui (Chat + IDE + Settings + Workflows + Skills)
│   └── gradio-ui/             # Gradio lightweight alternative UI
├── gateways/                  # پل‌های ارتباطی خارجی (Telegram, Webhooks)
└── packages/
    ├── magoco-core/           # هسته مرکزی: Agent + Tools + Memory + ReAct + Skills + LLM Gateway
    └── magoco-workflows/      # موتور اجرای گراف‌ها (DAG) و تسک‌های زمان‌بندی
```

## 🎨 قابلیت‌های اصلی

| دسته | ویژگی‌ها |
|------|----------|
| **Agent Chat** | Streaming زنده، بلوک‌های تفکر (Thinking Blocks)، Tool Cards |
| **Vibe-Coding IDE** | Monaco Editor + File Tree + Diff Preview (قبل/بعد) |
| **Workflow Designer** | ReactFlow Drag & Drop، گره‌های Agent/Tool/Condition |
| **Settings & LLM** | OpenAI/Ollama Hybrid، Memory Config، Prompt Management |
| **Skills Marketplace** | Registry، Loader، Auto-discovery، .skill.md (YAML frontmatter) |
| **Human-in-the-Loop** | Approval Gates (تأیید/رد)، Planning Panel، Clarification Questions |
| **Integrations Panel** | مدیریت اتصال سرویس‌ها (Slack, GitHub, Gmail, Notion, ... ) |
| **Execution History** | Audit Trail کامل با لاگ‌ها، وضعیت، زمان‌بندی |
| **Telegram Gateway** | Bot با Approval Inline Buttons، Voice، Topics |
| **Core Engine** | 3-Layer Memory، ReAct Agent، Multi-Agent Orchestrator (5 roles)، Self-Evolution Engine |

## 🚀 شروع سریع (Production Ready - Docker Compose)

### پیش‌نیازها
- Docker + docker-compose (v2+)

### نصب و اجرا (یک دستور)

```bash
# 1. کلون پروژه
git clone https://github.com/macmam1/MAGoCo-Self-Evo.git
cd MAGoCo-Self-Evo

# 2. تنظیم محیط (اختیاری - برای LLM واقعی)
cp .env.example .env
# ویرایش .env و اضافه کردن OPENAI_API_KEY یا OLLAMA_BASE_URL

# 3. اجرای همه سرویس‌ها
docker-compose up -d --build

# 4. بررسی سلامت
curl http://localhost:8000/health
# خروجی: {"status":"ok","version":"0.3.0","database":"sqlite"}

# 5. باز کردن UI
open http://localhost:5173
```

| سرویس | URL | توضیح |
|-------|-----|-------|
| **Frontend UI** | http://localhost:5173 | رابط اصلی (Chat, IDE, Workflows, Skills, Settings) |
| **Backend API** | http://localhost:8000 | FastAPI REST + WebSocket |
| **API Docs (Swagger)** | http://localhost:8000/docs | مستندات خودکار OpenAPI |
| **Health Check** | http://localhost:8000/health | وضعیت سرور و دیتابیس |

> **نکته:** پیش‌فرض دیتابیس **SQLite** است (صفر وابستگی). برای PostgreSQL در Production، پروفایل `with-db` را فعال کنید: `docker-compose --profile with-db up -d`

## 🛠️ توسعه محلی (بدون Docker)

### Backend
```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -e ../../packages/magoco-core -e ../../packages/magoco-workflows
pip install fastapi "uvicorn[standard]" sqlalchemy aiosqlite pydantic-settings httpx pyyaml openai
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd apps/frontend
npm install
npm run dev
```

## 📐 اصول معماری

- **🎯 ماژولار**: هر feature ماژول مستقل با interface واضح
- **🔌 Plugin-based**: Agentها، Storageها، LLM Providerها، Skills همه pluggable
- **🚩 Feature flags**: ویژگی‌ها قابل فعال/غیرفعال شدن بدون تغییر کد
- **🏛️ Hexagonal**: Business logic از infrastructure جدا
- **📦 Microservice-ready**: هر app مستقل deploy می‌شود
- **🔄 Self-Evolving**: Reflection → Pattern Mining → Skill Generation → Prompt Optimization

## 📚 مستندات بیشتر

- [معماری](docs/architecture.md)
- [راه‌اندازی Backend](apps/backend/README.md)
- [راه‌اندازی Frontend](apps/frontend/README.md)
- [راه‌اندازی Gradio](apps/gradio-ui/README.md)

## 📄 License

MIT