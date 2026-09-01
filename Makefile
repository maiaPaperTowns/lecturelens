.PHONY: help up down logs build test lint backend-test frontend-test train evaluate seed clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Build + start the full stack (frontend :3000, api :8000, db :5432)
	docker compose up --build

down: ## Stop the stack
	docker compose down

logs: ## Tail backend logs
	docker compose logs -f backend

build: ## Build all docker images
	docker compose build

test: backend-test frontend-test ## Run all tests

backend-test: ## Run backend tests + lint
	cd backend && ruff check app scripts tests && pytest -q

frontend-test: ## Run frontend tests + lint + typecheck
	cd frontend && npm run lint && npm run typecheck && npm test

lint: ## Lint backend + frontend
	cd backend && ruff check app scripts tests
	cd frontend && npm run lint

train: ## (Re)build training data + train models
	cd backend && python scripts/build_training_data.py && python scripts/train_models.py

evaluate: ## Compare sklearn vs PyTorch models
	cd backend && python scripts/evaluate_models.py

seed: ## Seed demo lectures into the database
	cd backend && python scripts/seed_demo_data.py

clean: ## Remove build artifacts + caches
	rm -rf frontend/dist frontend/coverage backend/.pytest_cache backend/.ruff_cache
	find backend -name __pycache__ -type d -prune -exec rm -rf {} +
