.PHONY: dev down logs api-shell web-shell migrate

dev:
	docker compose -f infra/docker/docker-compose.yml up --build

down:
	docker compose -f infra/docker/docker-compose.yml down

logs:
	docker compose -f infra/docker/docker-compose.yml logs -f

api-shell:
	docker compose -f infra/docker/docker-compose.yml exec api bash

web-shell:
	docker compose -f infra/docker/docker-compose.yml exec web sh

migrate:
	docker compose -f infra/docker/docker-compose.yml exec api uv run alembic upgrade head
