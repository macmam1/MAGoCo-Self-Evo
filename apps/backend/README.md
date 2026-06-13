# Backend (FastAPI)

API اصلی پروژه MAGoCo-Self-Evo.

## 🏗️ ساختار

```
backend/
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── api/             # HTTP routes
│   │   └── health.py
│   ├── core/            # Config, logging, security
│   │   ├── config.py
│   │   └── logging.py
│   ├── db/              # Database session
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic (ماژولار)
│   └── workers/         # Celery tasks
├── tests/
├── pyproject.toml
└── Dockerfile
```

## 🚀 اجرا (با Docker — توصیه‌شده)

```bash
# از root پروژه
make up
```

## 🛠️ اجرا (محلی — بدون Docker)

```bash
# نیاز: Python 3.11+ و uv
cd apps/backend

# نصب deps
uv sync

# اجرا
uv run uvicorn app.main:app --reload --port 8000
```

## 🧪 تست

```bash
# با Docker
make test

# یا محلی
uv run pytest

# با coverage
uv run pytest --cov=app --cov-report=html
```

## 📝 API Docs

بعد از اجرا:
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔌 افزودن Endpoint جدید

```python
# 1. ساخت router
# app/api/my_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"hello": "world"}

# 2. اضافه به main.py
# app/main.py
from app.api import my_feature
app.include_router(my_feature.router, prefix="/api/v1", tags=["my-feature"])
```

## 🛡️ متغیرهای محیطی

از root، `.env.example` رو به `.env` کپی کن. مهم‌ترین‌ها:
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `OPENAI_API_KEY` (اختیاری)
- `ANTHROPIC_API_KEY` (اختیاری)
- `HUGGINGFACE_API_KEY` (اختیاری)

## 📐 اصول

- **ماژولار**: هر feature یه ماژول مستقل
- **Async-first**: از async/await استفاده کن
- **Type hints**: همه جا type hint لازم
- **Pydantic v2**: برای validation
- **SQLAlchemy 2.0**: async ORM
