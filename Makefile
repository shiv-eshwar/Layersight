.PHONY: setup test dev api web db db-stop simulate compare recommend validate demo types e2e e2e-app rehearse video perf offline-check demo-check

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
	uv run ruff check api engine/tests/test_contracts.py engine/tests/test_corpus.py engine/tests/test_reference.py engine/layersight/__init__.py engine/layersight/models.py engine/layersight/config/schema.py engine/layersight/refs.py
	uv run ruff format --check api engine/tests/test_contracts.py engine/tests/test_corpus.py engine/tests/test_reference.py engine/layersight/__init__.py engine/layersight/models.py engine/layersight/config/schema.py engine/layersight/refs.py
	uv run mypy
	uv run pytest
	pnpm --dir web exec tsc --noEmit
	pnpm --dir web exec eslint .

simulate:
	uv run layersight simulate data/test/emails \
		--config data/test/configs/untrained.yaml --runs 10000 --seed 42

compare:
	uv run layersight compare data/test/emails \
		--a data/test/configs/untrained.yaml \
		--b data/test/configs/trained.yaml --runs 10000 --seed 42

validate:
	uv run layersight validate data/test/emails --labels data/test/labels.csv

recommend:
	uv run layersight recommend data/test/emails \
		--config data/test/configs/untrained.yaml

e2e:
	./scripts/demo/e2e.sh

e2e-app:
	cd web/e2e && E2E_TARGET=app pnpm exec playwright test app-path.spec.ts

rehearse:
	./scripts/demo/rehearse.sh

video:
	./scripts/demo/record-backup.sh

perf:
	./scripts/demo/perf-check.sh

offline-check:
	./scripts/demo/offline-check.sh

demo-check: offline-check perf e2e

demo:
	uv run python -m app.demo_seed

types:
	uv run python scripts/export_openapi.py
	pnpm --dir web exec openapi-typescript ../api/openapi.json -o lib/api-types.ts
