.PHONY: up down logs build rebuild clean help ps test shell

help:
	@echo "Guess the Country - Docker Commands"
	@echo "===================================="
	@echo ""
	@echo "make up       - Build and start the app"
	@echo "make down     - Stop the app"
	@echo "make rebuild  - Rebuild image and start fresh"
	@echo "make logs     - Follow logs"
	@echo "make ps       - Show container status"
	@echo "make test     - Run backend tests inside the container"
	@echo "make shell    - Shell into the container"
	@echo "make clean    - Stop and remove containers and images"
	@echo ""
	@echo "Once running, everything is on ONE port:"
	@echo "  - Game:     http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo ""

up:
	docker-compose up -d --build
	@echo "Game running at http://localhost:8000"

down:
	docker-compose down

logs:
	docker-compose logs -f

build:
	docker-compose build

rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

ps:
	docker-compose ps

test:
	docker-compose exec app python -m pytest tests/ -v

shell:
	docker-compose exec app /bin/bash

clean:
	docker-compose down -v --rmi local
	@echo "Cleaned up"
