.PHONY: up down dev-backend dev-frontend lint test migrate

up:
	docker compose up -d

down:
	docker compose down

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

lint:
	cd backend && ruff check .
	cd backend && mypy app

test:
	cd backend && pytest ../tests/backend
