# PokeUK DealScout - Development Commands
# ========================================

.PHONY: help install dev db-up db-down db-reset api scrape test lint clean

# Default target
help:
	@echo "PokeUK DealScout - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install all dependencies"
	@echo "  make dev         - Install in development mode"
	@echo ""
	@echo "Database:"
	@echo "  make db-up       - Start PostgreSQL and Redis (Docker)"
	@echo "  make db-down     - Stop database containers"
	@echo "  make db-reset    - Reset database (drop and recreate)"
	@echo "  make db-migrate  - Run database migrations"
	@echo ""
	@echo "Run:"
	@echo "  make api         - Start FastAPI backend server"
	@echo "  make scrape      - Run scrapers once"
	@echo "  make frontend    - Start Next.js frontend"
	@echo ""
	@echo "Quality:"
	@echo "  make test        - Run all tests"
	@echo "  make lint        - Run linter (ruff)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Remove cache files and build artifacts"

# ==================
# Setup
# ==================

install:
	cd backend && pip install -e .
	cd scrapers && pip install -e .
	cd scrapers && playwright install chromium

dev:
	cd backend && pip install -e ".[dev]"
	cd scrapers && pip install -e ".[dev]"
	cd scrapers && playwright install chromium

# ==================
# Database
# ==================

db-up:
	docker compose up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d
	@sleep 3
	cd backend && python -m scripts.init_db

db-migrate:
	cd backend && alembic upgrade head

# ==================
# Run Services
# ==================

api:
	cd backend && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

scrape:
	cd scrapers && python -m scrapers.run_once

frontend:
	cd frontend && npm run dev

# ==================
# Quality
# ==================

test:
	cd backend && pytest -v
	cd scrapers && pytest -v

lint:
	cd backend && ruff check .
	cd scrapers && ruff check .

# ==================
# Cleanup
# ==================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
