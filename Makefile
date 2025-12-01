.PHONY: up down test fmt lint clean migrate seed worker worker-dry-run scan setup-env

# Default target
.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  make setup-env     - Create .env files from examples"
	@echo "  make up            - Start all services with docker compose"
	@echo "  make down          - Stop all services"
	@echo "  make migrate       - Run database migrations"
	@echo "  make seed          - Seed demo data (10 customers, 25 events)"
	@echo "  make scan          - Run scanner against configured source databases"
	@echo "  make worker        - Run identity worker to process customers"
	@echo "  make worker-dry-run - Run identity worker in dry-run mode"
	@echo "  make test          - Run tests"
	@echo "  make fmt           - Format code with Black and Ruff"
	@echo "  make lint          - Lint code with Ruff"
	@echo "  make clean         - Clean up containers and volumes"

setup-env:
	@echo "Setting up environment files..."
	@./scripts/setup-env.sh

up:
	@echo "Starting Enterprise DNA services..."
	@if [ ! -f .env ]; then \
		echo "⚠ Warning: .env file not found. Run 'make setup-env' first."; \
		echo "Continuing with defaults..."; \
	fi
	docker compose up -d
	@echo "Services started. API Gateway: http://localhost:8000"

down:
	@echo "Stopping Enterprise DNA services..."
	docker compose down

migrate:
	@echo "Running database migrations..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi; \
	python3 scripts/run_migrations.py

seed:
	@echo "Seeding demo data..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi; \
	python3 scripts/seed_demo_data.py

worker:
	@echo "Running identity worker..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi; \
	docker compose run --rm identity-worker python -m identity_worker.main

worker-dry-run:
	@echo "Running identity worker (dry-run)..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi; \
	docker compose run --rm identity-worker python -m identity_worker.main --dry-run

scan:
	@echo "Running scanner against configured source databases..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi; \
	docker compose run --rm scanner

test:
	@echo "Running tests..."
	pytest tests/ -v

fmt:
	@echo "Formatting code..."
	black apps/ packages/ tests/
	ruff check --fix apps/ packages/ tests/

lint:
	@echo "Linting code..."
	ruff check apps/ packages/ tests/
	black --check apps/ packages/ tests/

clean:
	@echo "Cleaning up..."
	docker compose down -v
	docker system prune -f

