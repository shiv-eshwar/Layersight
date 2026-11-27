.PHONY: setup test dev api web db db-stop simulate compare recommend e2e rehearse video perf offline-check demo-check

# Postgres in Docker when it is available, then the API and the web app on the host.
dev:
	@docker info >/dev/null 2>&1 && docker compose up -d db || echo "Docker is not running, so Postgres was not started. The API does not need it yet."
	@set -eu; \
	trap 'kill 0' INT TERM EXIT; \
	uv run uvicorn app.main:app --reload --port 8000 --app-dir api & \
	pnpm --dir web dev & \
	wait

api:
	uv run uvicorn app.main:app --reload --port 8000 --app-dir api

web:
	pnpm --dir web dev

db:
	docker compose up -d db

db-stop:
	docker compose stop db


setup:
	cd engine && uv sync --all-groups

test:
	cd engine && uv run ruff check layersight tests \
		&& uv run ruff format --check layersight tests \
		&& uv run mypy \
		&& uv run pytest

simulate:
	cd engine && uv run layersight simulate ../data/dev/analyses \
		--config ../data/dev/configs/untrained.yaml --runs 10000 --seed 42

compare:
	cd engine && uv run layersight compare ../data/dev/analyses \
		--a ../data/dev/configs/untrained.yaml \
		--b ../data/dev/configs/trained.yaml --runs 10000 --seed 42

recommend:
	cd engine && uv run layersight recommend ../data/dev/analyses \
		--config ../data/dev/configs/untrained.yaml

e2e:
	./scripts/demo/e2e.sh

rehearse:
	./scripts/demo/rehearse.sh

video:
	./scripts/demo/record-backup.sh

perf:
	./scripts/demo/perf-check.sh

offline-check:
	./scripts/demo/offline-check.sh

demo-check: offline-check perf e2e
