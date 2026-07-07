# ⚡ Texas Grid Stress Observatory

A local-first data platform that **measures and predicts stress on the Texas (ERCOT) power grid** by fusing three data sources:

1. **Real ERCOT grid data** — system load and fuel mix, pulled via [`gridstatus`](https://docs.gridstatus.io)
2. **Real Texas weather** — hourly conditions for five cities via the free [Open-Meteo](https://open-meteo.com) API
3. **A simulated fleet of ~300 residential smart meters** — whose HVAC demand reacts to the *real* temperatures from source #2

Everything lands in a TimescaleDB warehouse, is modeled with dbt (raw → staging → marts), gated by data-quality tests, and served in a Streamlit dashboard as a **Grid Strain Index** — a NORMAL / ELEVATED / CRITICAL classification of every 5-minute interval, alongside the demand-vs-temperature relationship that drives it.

> **Why this project?** Companies like Base Power deploy distributed batteries that *respond* to grid stress. This platform builds the *demand and strain signal* such a fleet would dispatch against — the complementary side of the same problem.

## Architecture

```
ERCOT load + fuel mix ─┐  (batch, gridstatus)
Open-Meteo weather ────┼─► RAW (TimescaleDB) ─► dbt staging ─► marts ─► Streamlit
Smart-meter fleet ─────┘  (streaming simulator)        │
                                                       └─ data-quality tests gate everything
```

**Key marts:** `fct_grid_strain` (load vs. capacity, temp-adjusted) · `fct_demand_weather` (how °F drives kW, per city) · `fct_meter_health` (fleet reporting rates, offline events)

## Stack

Docker Compose · TimescaleDB · Python 3.11 · dbt · Streamlit/Plotly · reference Airflow DAG — developed in PyCharm Professional + DataGrip.

## Quickstart

```bash
cp .env.example .env
make up        # db + streaming meter fleet + dbt + dashboard
make refresh   # ingest grid + weather, dbt build (models + tests)
```

Then open http://localhost:8501. Requires only Docker; `make` is a convenience (every target wraps a plain `docker compose` command).

## Build progress

Built in public, one phase per day:

- [x] **Day 1 — Foundation:** Docker Compose, TimescaleDB warehouse, raw schema (4 hypertables)
- [ ] **Day 2 — Batch ingest:** ERCOT load + fuel mix, idempotent, real/synthetic sources
- [ ] **Day 3 — Batch ingest:** Open-Meteo weather for Austin, Houston, Dallas, San Antonio, Midland
- [ ] **Day 4 — Streaming:** smart-meter fleet simulator with weather-driven HVAC load + lifecycle events
- [ ] **Day 5 — dbt:** staging, three marts, schema + custom data-quality tests
- [ ] **Day 6 — Serving:** strain dashboard + local scheduler
- [ ] **Day 7 — Polish:** production story (Airflow, cloud mapping), strain-drivers analysis notebook

## Design decisions

- **Continuous telemetry and discrete events live in separate tables** — they have different grains and different consumers.
- **The strain index lives in a tested dbt mart, not application code** — the dashboard and any downstream consumer only ever touch canonical, quality-gated data.
- **Every source has a synthetic fallback** so a fresh clone runs offline with zero API keys — but the default configuration uses real ERCOT and real weather data.

## Local → production mapping

| Local (this repo)     | Production analogue               |
|-----------------------|-----------------------------------|
| TimescaleDB in Docker | BigQuery / Snowflake              |
| Python producer loop  | Kafka / Kinesis + stream consumer |
| Local scheduler loop  | Airflow (see `orchestration/`)    |
| docker compose        | Terraform-provisioned cloud infra |
| Streamlit             | Looker / Grafana                  |