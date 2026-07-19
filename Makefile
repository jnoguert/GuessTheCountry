.PHONY: up down logs build rebuild clean help ps

help:
	@echo "Guess the Country - Docker Commands"
	@echo "===================================="
	@echo ""
	@echo "make up          - Start the full stack (backend + frontend)"
	@echo "make down        - Stop the full stack"
	@echo "make rebuild     - Rebuild images and start"
	@echo "make logs        - Show logs from both services"
	@echo "make logs-backend - Show backend logs only"
	@echo "make logs-frontend - Show frontend logs only"
	@echo "make ps          - Show running containers"
	@echo "make clean       - Stop and remove containers, volumes, images"
	@echo ""
	@echo "Once running:"
	@echo "  - Frontend: http://localhost:5173"
	@echo "  - Backend:  http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo ""

up:
	docker-compose up -d
	@echo "✓ Services starting..."
	@echo "  Frontend: http://localhost:5173"
	@echo "  Backend:  http://localhost:8000"

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

build:
	docker-compose build

rebuild: clean build up

ps:
	docker-compose ps

clean:
	docker-compose down -v
	docker image rm guess-the-country-backend guess-the-country-frontend 2>/dev/null || true
	@echo "✓ Cleaned up"

test-backend:
	docker-compose exec backend pytest tests/

shell-backend:
	docker-compose exec backend /bin/bash

shell-frontend:
	docker-compose exec frontend /bin/sh
