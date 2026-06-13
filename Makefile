.PHONY: help install up down logs build test clean backend frontend format lint

# Default
help:
	@echo "MAGoCo-Self-Evo — Commands:"
	@echo ""
	@echo "  make install     # اولین نصب (deps + env)"
	@echo "  make up          # اجرای همه سرویس‌ها"
	@echo "  make down        # توقف همه سرویس‌ها"
	@echo "  make logs        # نمایش logs"
	@echo "  make build       # build images"
	@echo "  make test        # اجرای تست‌ها"
	@echo "  make backend     # shell داخل backend container"
	@echo "  make frontend    # shell داخل frontend container"
	@echo "  make format      # format code"
	@echo "  make lint        # lint code"
	@echo "  make clean       # پاک کردن همه چیز (data + volumes)"

# ===== Setup =====
install:
	@if [ ! -f .env ]; then cp .env.example .env && echo "✅ .env ساخته شد"; fi
	@echo "✅ آماده. حالا 'make up' بزن."

# ===== Docker =====
up:
	docker-compose up -d
	@echo "✅ همه سرویس‌ها بالا اومدن"
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"

down:
	docker-compose down

logs:
	docker-compose logs -f

build:
	docker-compose build

# ===== Shell access =====
backend:
	docker-compose exec backend bash

frontend:
	docker-compose exec frontend sh

db:
	docker-compose exec postgres psql -U magoco -d magoco

redis:
	docker-compose exec redis redis-cli

# ===== Testing =====
test:
	docker-compose exec backend pytest
	docker-compose exec frontend pnpm test

# ===== Quality =====
format:
	docker-compose exec backend ruff format .
	docker-compose exec backend ruff check --fix .
	docker-compose exec frontend pnpm format

lint:
	docker-compose exec backend ruff check .
	docker-compose exec frontend pnpm lint

# ===== Cleanup =====
clean:
	docker-compose down -v
	@echo "⚠️  همه volumes و data پاک شدن"
