# Shared Package

اشتراک‌گذاری types، schemas و utilities بین backend و frontend.

## 📦 محتوا

- `types/` — TypeScript types (mirror از Pydantic schemas)
- `schemas/` — JSON schemas
- `constants/` — مقادیر ثابت مشترک
- `utils/` — توابع کمکی

## 🔄 نحوه استفاده

### در Frontend
```ts
// apps/frontend/package.json
{
  "dependencies": {
    "@magoco/shared": "workspace:*"
  }
}
```

### در Backend
```python
# apps/backend/pyproject.toml
[tool.uv.sources]
shared = { path = "../../packages/shared" }
```

## 📝 افزودن Type/Schema جدید

1. اضافه به `types/` (TypeScript)
2. اضافه به `schemas/` (JSON Schema)
3. در backend Pydantic model تعریف کن
4. Export از `index.ts` و `__init__.py`
