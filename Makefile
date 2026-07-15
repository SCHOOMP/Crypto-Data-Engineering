.PHONY: up down psql logs clean seed-grid seed-weather refresh

HOURS ?= 24

up:
	docker compose up -d --build

down:
	docker compose down

psql:
	docker compose exec db psql -U grid -d grid_observatory

logs:
	docker compose logs -f meters

clean:
	docker compose down -v

seed-grid:
	docker compose exec ingestion python ercot_load.py $(if $(SOURCE),--source $(SOURCE)) --hours $(HOURS)

seed-weather:
	docker compose exec ingestion python weather.py

refresh: seed-grid seed-weather