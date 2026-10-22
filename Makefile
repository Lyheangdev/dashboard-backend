bootstrap:
	python -m src.bootstrap
	
init:
	uv init

dev:
	uv run fastapi dev

sync:
	uv sync 

init-migration:
	uv run alembic init alembic

alembic:
	uv run alembic $(filter-out $@,$(MAKECMDGOALS))

migrate:
	uv run alembic revision --autogenerate -m "$(msg)"

migrate_up:
	uv run alembic upgrade head

migrate_down:
	uv run alembic downgrade $(or $(revision), -1)

rollback_all:
	uv run alembic downgrade base

format:
	uv run ruff format .

check:
	uv run ruff format --check .

quality:
	uv run ruff check .

fix:
	uv run ruff check --fix .

%:
	@:

