# Reminder 05 — HF Spaces Compatibility (ADR-006)

> **تاریخ:** ۱۴۰۵/۰۳/۲۳
> **منبع:** huggingface.co/docs/hub/spaces-overview + spaces-sdks-docker
> **وضعیت:** ✅ نهایی

## ADR-006: HF Spaces Production Strategy

### Context
پروژه باید روی **Hugging Face Spaces (free tier)** قابل deploy باشه. محدودیت‌های رسمی:

| محدودیت | مقدار |
|---------|-------|
| CPU | 2 vCPU |
| RAM | 16 GB |
| Disk | 50 GB (NOT persistent) |
| User ID | 1000 (non-root) |
| Default port | 7860 |
| Storage | Ephemeral + HF Datasets |
| Sleep | بعد از inactivity |
| Secrets | از Settings tab |

### Decision: Hybrid Architecture

**Dev (local):** همون docker-compose فعلی (5 services)
**Production (HF):** Single container + external services

```
┌─────────────────────────────────────────┐
│   Hugging Face Space (1 container)      │
│   ┌─────────────────────────────────┐   │
│   │  Nginx (reverse proxy :7860)    │   │
│   │   ├─ /          → frontend      │   │
│   │   ├─ /api/*     → FastAPI :8000 │   │
│   │   └─ /gradio/*  → Gradio :7861  │   │
│   └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │ (outbound HTTPS)
   ┌───────────┼───────────┐
   ▼           ▼           ▼
┌──────┐  ┌────────┐  ┌─────────┐
│ Neon │  │Upstash │  │   HF    │
│  PG  │  │ Redis  │  │Datasets │
│(free)│  │ (free) │  │ (free)  │
└──────┘  └────────┘  └─────────┘
```

### Consequences

**✅ سازگار:**
- Monorepo structure (dev) + production Dockerfile
- FastAPI + async (کارایی بالا)
- Storage adapter pattern (HF Datasets support)
- LLM provider abstraction (multi-provider)
- Nginx برای multi-port
- Background tasks (به جای Celery worker جدا)
- Lazy loading برای models

**❌ محدودیت‌هایی که باید پذیرفت:**
- بدون Celery worker جدا → background tasks درون‌فرآیندی
- بدون PostgreSQL local → external (Neon/Supabase)
- بدون Redis local → external (Upstash)
- Storage فایل → HF Datasets
- Sleep بعد از inactivity → نیاز keep-alive یا upgrade

### External Services (همه رایگان)

| سرویس | ارائه‌دهنده | پلن رایگان |
|-------|-------------|-----------|
| PostgreSQL | Neon / Supabase | 0.5 GB / 500 MB |
| Redis | Upstash | 10K cmd/day |
| Storage | HF Datasets | Unlimited (public) |
| Email | Resend | 100 emails/day |
| Sentry | Sentry | 5K events/month |

### Implementation Plan

1. ✅ Production Dockerfile (multi-stage: backend + frontend build + nginx)
2. ✅ docker-compose با profiles (`dev` / `prod`)
3. ✅ Nginx config داخلی
4. ✅ Health check + readiness probe
5. ✅ External services config (env vars)
6. ✅ Migration path: dev → prod

### Compliance Checklist (برای deploy)

- [ ] Dockerfile با user ID 1000
- [ ] app_port: 7860 در README
- [ ] Health check endpoint
- [ ] Secrets از env vars (نه hardcode)
- [ ] /data volume برای runtime state
- [ ] Lazy loading models
- [ ] Connection pooling برای external DB
- [ ] Cache TTL برای Redis
- [ ] Fallback strategy برای external services outage
