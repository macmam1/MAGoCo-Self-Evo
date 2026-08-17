FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies manifests
COPY apps/backend/pyproject.toml /app/apps/backend/
COPY packages/magoco-core /app/packages/magoco-core
COPY packages/magoco-workflows /app/packages/magoco-workflows

# Install core packages in editable mode + backend dependencies
RUN pip install --no-cache-dir -e /app/packages/magoco-core \
    && pip install --no-cache-dir -e /app/packages/magoco-workflows \
    && pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy aiosqlite pydantic-settings httpx pyyaml openai

# Copy full backend application
COPY apps/backend /app/apps/backend

WORKDIR /app/apps/backend

# Set environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/magoco-core:/app/packages/magoco-workflows

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]