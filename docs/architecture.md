# Architecture — معماری MAGoCo-Self-Evo

## 🏛️ نمای کلی

```
┌────────────────────────────────────────────────────────┐
│              Frontend (Vite + React)                    │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │Dashboard │ │Workflow Maker│ │     Chat UI      │  │
│  └──────────┘ └──────────────┘ └──────────────────┘  │
└─────────────────────┬──────────────────────────────────┘
                      │ REST + WebSocket
┌─────────────────────┴──────────────────────────────────┐
│                Backend (FastAPI)                         │
│  ┌────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐    │
│  │  Auth  │ │  Agents  │ │Workflows│ │  Files   │    │
│  └────────┘ └──────────┘ └─────────┘ └──────────┘    │
└──┬──────────┬──────────┬──────────┬──────────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
┌──────┐  ┌───────┐  ┌───────┐  ┌─────────┐
│  PG  │  │ Redis │  │Celery │  │ Storage │
│      │  │       │  │       │  │  Layer  │
└──────┘  └───────┘  └───────┘  └────┬────┘
                                     │
                       ┌─────────────┼─────────────┐
                       ▼             ▼             ▼
                   ┌───────┐    ┌───────┐    ┌───────┐
                   │  HF   │    │  S3   │    │ Local │
                   │Dataset│    │  GCS  │    │  FS   │
                   └───────┘    └───────┘    └───────┘
```

## 🔧 Tech Stack (نهایی)

| لایه | تکنولوژی | دلیل |
|------|----------|------|
| **Frontend** | Vite + React 18 + TypeScript | سریع، type-safe، اکوسیستم بزرگ |
| **UI** | Tailwind + shadcn/ui | توسعه سریع، تمیز |
| **State** | Zustand + TanStack Query | سبک، ساده |
| **Forms** | React Hook Form + Zod | type-safe validation |
| **i18n** | i18next | پشتیبانی فارسی + انگلیسی |
| **Workflow** | React Flow | قدرتمند، drag-drop |
| **Backend** | FastAPI | async، سریع، docs auto |
| **ORM** | SQLAlchemy 2.0 + asyncpg | type-safe async |
| **Migrations** | Alembic | استاندارد |
| **Queue** | Celery + Redis | reliable async tasks |
| **Auth** | JWT (PyJWT) | استاندارد، ساده |
| **Agent** | CrewAI | multi-agent orchestration |
| **LLM** | Multi-provider | OpenAI/Anthropic/HF/Ollama |
| **Vector DB** | Qdrant | برای agent memory |
| **Storage** | Adapter pattern | HF/S3/GCS/Local |
| **Testing** | pytest + Vitest | استاندارد |
| **CI/CD** | GitHub Actions | رایگان، یکپارچه |
| **Deploy** | HF Spaces + Docker | رایگان + انعطاف |

## 📁 Monorepo

```
MAGoCo-Self-Evo/
├── apps/
│   ├── backend/       FastAPI
│   ├── frontend/      Vite + React
│   └── gradio-ui/     Gradio
├── packages/
│   └── shared/        types/schemas مشترک
├── docs/
├── docker-compose.yml
└── Makefile
```

## 🎯 اصول معماری

### 1. ماژولاریتی
- **Plugin architecture**: agent ها، LLM provider ها، storage adapter ها همه pluggable
- **Hexagonal architecture**: business logic از infrastructure جدا
- **Loose coupling**: هر ماژول مستقل، interface-based

### 2. Feature Flags
```python
# app/core/feature_flags.py
FEATURES = {
    "self_evolution": True,
    "workflow_maker": True,
    "file_manager": True,
    "external_services": False,  # بعداً فعال میشه
}
```

### 3. Adapter Pattern (Storage)
```python
class StorageBackend(Protocol):
    async def save(self, key: str, data: bytes) -> str: ...
    async def load(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...

# پیاده‌سازی‌ها
class LocalStorage: ...
class HFDatasetsStorage: ...
class S3Storage: ...
class GCSStorage: ...
```

### 4. Multi-Provider LLM
```python
class LLMProvider(Protocol):
    async def complete(self, prompt: str, **kwargs) -> str: ...

class OpenAIProvider: ...
class AnthropicProvider: ...
class HFProvider: ...
class OllamaProvider: ...
```

### 5. Plugin Architecture (Agents)
```python
class AgentPlugin(Protocol):
    name: str
    role: str
    tools: list[Tool]

# ثبت agent جدید
@agent_registry.register
class MyCustomAgent:
    name = "my_agent"
    role = "specialized task"
    tools = [...]
```

## 🔐 Security

- JWT با rotation
- bcrypt password hashing
- CORS محدود
- Input validation (Pydantic + Zod)
- SQL injection safe (ORM)
- HTTPS در production
- Secrets در env vars (نه hardcode)

## 🚀 Deployment

### سطح ۱: Local Dev
```bash
make up
```

### سطح ۲: HF Spaces
- Gradio app در Space
- Backend در همون Space (single container)

### سطح ۳: Production
- Backend: VPS / Cloud Run
- Frontend: Vercel / Cloudflare Pages
- DB: managed Postgres (Neon, Supabase)
- Storage: S3 / R2
