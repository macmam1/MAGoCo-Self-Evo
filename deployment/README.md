# MAGoCo-Self-Evo 🤗

> Multi-Agent Go-Coordinator with Self-Evolution

A self-hosted, modular platform for building, orchestrating and evolving AI agents.

## 🏗️ Architecture

Single container with Nginx reverse proxy:

- `/` → Static frontend (Vite + React)
- `/api/*` → FastAPI backend
- `/gradio/*` → Simple Gradio interface
- `/docs` → Swagger UI

## 🚀 Local Development

See [README.md](../README.md) for full setup.

## ☁️ Deploy to Hugging Face Spaces

### 1. Create a new Space
- Go to https://huggingface.co/new-space
- SDK: **Docker**
- Visibility: Public / Private
- Hardware: CPU basic (free)

### 2. Push code
```bash
# Add HF remote
git remote add hf https://huggingface.co/spaces/USERNAME/MAGoCo-Self-Evo
git checkout -b main

# Copy production files
cp deployment/Dockerfile.production Dockerfile
cp deployment/README.hf.md README.md
cp apps/gradio-ui/app.py gradio_app.py
cp -r apps/frontend apps/backend packages .

# Push
git add .
git commit -m "Deploy to HF Space"
git push hf main
```

### 3. Configure Secrets (in Space Settings)

**Required:**
- `DATABASE_URL` — PostgreSQL connection string (Neon/Supabase)
- `REDIS_URL` — Redis connection string (Upstash)
- `JWT_SECRET_KEY` — Random 32+ char secret
- `OPENAI_API_KEY` — (or other LLM provider)

**Optional:**
- `HF_STORAGE_REPO` — HF Dataset repo for file storage
- `HUGGINGFACE_API_KEY` — For HF models
- `ANTHROPIC_API_KEY` — Claude support

### 4. External Services (Free Tier)

| Service | Provider | URL |
|---------|----------|-----|
| PostgreSQL | [Neon](https://neon.tech) | https://neon.tech |
| Redis | [Upstash](https://upstash.com) | https://upstash.com |
| Storage | HF Datasets | Built-in |

## 📚 Documentation

- [Full README](../README.md)
- [Architecture](../docs/architecture.md)
- [API Reference](https://hf.co/docs)

## 📄 License

MIT
