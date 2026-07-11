.PHONY: up down psql logs clean ingest

HOURS ?= 24

up:
	docker compose up -d --build

down:
	docker compose down

psql:
	docker compose exec db psql -U grid -d grid_observatory

logs:
	docker compose logs -f

clean:
	docker compose down -v

ingest:
	docker compose exec ingestion python ercot_load.py $(if $(SOURCE),--source $(SOURCE)) --hours $(HOURS)