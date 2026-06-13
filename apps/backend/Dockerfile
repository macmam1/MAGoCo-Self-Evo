# ===== Stage 1: Base =====
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ===== Stage 2: Dependencies =====
FROM base AS deps

# Install uv (fast Python package manager)
RUN pip install uv

# Copy pyproject
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system --no-cache .

# ===== Stage 3: Development =====
FROM deps AS development

# Install dev deps
RUN uv pip install --system --no-cache ".[dev]"

# Copy app
COPY . .

# Create storage dir
RUN mkdir -p /app/storage

EXPOSE 8000

# Hot reload in dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===== Stage 4: Production =====
FROM deps AS production

# Copy app
COPY . .

# Create non-root user
RUN useradd -m -u 1000 magoco && \
    mkdir -p /app/storage && \
    chown -R magoco:magoco /app

USER magoco

EXPOSE 8000

# Production: multiple workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
