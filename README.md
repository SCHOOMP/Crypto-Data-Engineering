# Crypto Data Engineering — BTC Price Pipeline

A learning-focused data engineering project that ingests historical Bitcoin price
data into Postgres through a fast, **idempotent** load pipeline. Built to practice
the core skills of production data work: schema design, bulk loading, data quality,
and safe re-runnability.

---

## Overview

This project pulls raw Bitcoin OHLCV (open / high / low / close / volume) candle data
from a flat file and loads it into a Postgres database running in Docker. The load is
designed to be **safe to run any number of times without creating duplicate rows** —
the property that makes a pipeline production-ready and schedulable.

The guiding principle throughout: *simple, reliable systems that solve the real
problem — not over-engineered ones.*

---

## How the load works

The pipeline separates **raw landing** from the **load mechanics**, and gets both
speed and idempotency by splitting the load into two steps:

1. **COPY into staging** — the CSV is bulk-loaded into a constraint-free
   `staging_bitcoin` table using Postgres `COPY` (far faster than row-by-row
   INSERTs). Staging is dropped and recreated fresh every run.
2. **Merge into `bitcoin_raw`** — a single `INSERT ... SELECT ... ON CONFLICT
   (ts_epoch) DO NOTHING` moves rows from staging into the real table, skipping any
   timestamp that already exists.

Why two steps? `COPY` is fast but can't skip conflicts mid-stream. Staging lets the
fast load happen first, then the conflict-aware merge handles deduplication second —
so the pipeline is **both fast and idempotent**.

> Re-running the load reports `+0 new` rows on the second pass — proof it's safe to
> re-run.

---

## Tech stack

- **Database:** PostgreSQL 16 (running in Docker)
- **Language:** Python 3.13
- **Libraries:** pandas, SQLAlchemy, psycopg2-binary, python-dotenv
- **Bulk load:** Postgres `COPY` via `copy_expert`
- **Containerization:** Docker / Docker Compose

---

## Project structure

```
Crypto-Data-Engineering/
├── docker-compose.yml      # Postgres service + named volume
├── .env                    # DB credentials (gitignored)
├── .env.example            # template showing required variables
├── requirements.txt        # pinned Python dependencies
├── load/
│   └── load_to_DB.py       # the ingestion pipeline
└── data/
    └── btc/raw/            # source CSV(s)
```

---

## Getting started

### 1. Start the database

```bash
docker compose up -d
docker compose ps          # confirm the container is "Up (healthy)"
```

### 2. Configure credentials

Copy `.env.example` to `.env` and fill in your values:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=<your_db_name>
DB_USER=<your_user>
DB_PASSWORD=<your_password>
```

### 3. Create the table + unique constraint (one time)

```sql
-- run in DataGrip or psql
CREATE TABLE bitcoin_raw ( ... );   -- see schema notes
ALTER TABLE bitcoin_raw ADD CONSTRAINT bitcoin_raw_ts_unique UNIQUE (ts_epoch);
```

### 4. Run the load

```bash
python load/load_to_DB.py
```

Run it twice — the second run should report `+0 new`, confirming idempotency.

---

## Data source

Historical BTC minute-level OHLCV data (`<source / Kaggle dataset name>`).
~7.6M rows back to 2012. Timestamp stored as **Unix epoch (BIGINT)**; prices stored
as `NUMERIC` to preserve decimal precision. The raw file contains gap rows (no trades)
that the raw layer tolerates and a later cleaning step will handle.

---

## Roadmap / Next steps

- [ ] **Modeled layer** — convert epoch → timestamp, aggregate minute bars to hourly,
      handle gap rows deliberately (raw stays immutable).
- [ ] **Data quality tests (dbt)** — uniqueness, not-null, accepted ranges, gap
      detection, so bad data fails loudly before it reaches anyone.
- [ ] **Second source** — add ETH and a live API (CoinGecko); key becomes
      `(symbol, ts_epoch)`.
- [ ] **Orchestration** — schedule with Airflow / Prefect; retries + backfills
      (idempotent load makes re-runs safe).
- [ ] **Infrastructure-as-code** — define warehouse + storage in Terraform on AWS.

---

## Dev Log / Notes

> Running log of decisions and what I learned. Newest at the bottom.

### Day 1 — Design on paper
- Picked the project: a daily-style analytics pipeline on crypto price data.
- Worked out the **grain**: one row = one time-bucket of BTC price activity.
- Decided keys: natural key is the timestamp for a single coin; becomes the composite
  `(symbol, timestamp)` once a second coin (ETH) is added.
- Sketched the raw table columns (ts_epoch, open, high, low, close, volume) in a data
  dictionary before writing any code.

### Day 2 — Database in Docker
- Wrote `docker-compose.yml` for Postgres 16 with a healthcheck and a named volume
  (`pgdata`) so data survives container restarts.
- Hit an "undefined volume" error — learned named volumes must also be declared in a
  top-level `volumes:` block, not just referenced inside the service.
- Pulled DB credentials into a `.env` file and gitignored it (keep secrets out of git).
- Confirmed the connection from DataGrip.

### Day 3 — Schema + raw table
- Wrote `CREATE TABLE bitcoin_raw`. Key decisions:
  - Prices/volume as `NUMERIC` (not INT) — INT would truncate decimals; NUMERIC avoids
    float rounding errors.
  - Timestamp as `BIGINT` (Unix epoch) to match the raw file format; conversion to a
    real TIMESTAMP is a job for the modeled layer.
  - Surrogate `id` via `GENERATED ALWAYS AS IDENTITY` so raw rows always land.
  - Prices nullable in raw, because the source file has NaN gap rows.

### Day 4 — Inspecting + first load attempts
- Inspected the CSV: ~7.6M minute-level rows back to 2012, epoch timestamp, decimal
  prices, gap rows present.
- First tried `pandas.to_sql` defaults — far too slow (row-by-row INSERTs).
- Fixed a `psycopg2` build error by installing `psycopg2-binary` (no local pg_config /
  compiler needed; common on Python 3.13).

### Day 5 — Fast load with COPY
- Replaced default inserts with a custom `psql_copy` method using Postgres `COPY` via
  `copy_expert` — dramatically faster.
- Learned the trade-off: COPY is a firehose, can't dodge conflicts mid-stream.

### Day 6 — Idempotency (the big one)
- Added a `UNIQUE` constraint on `ts_epoch`.
- Built the **staging-then-merge** pattern: COPY into a fresh `staging_bitcoin`, then
  `INSERT ... ON CONFLICT (ts_epoch) DO NOTHING` into `bitcoin_raw`, all in one
  transaction (`engine.begin()`).
- Added before/after row counts as a built-in proof.
- **Verified:** first run loaded 7.6M rows; second run reported `+0 new`. Pipeline is
  idempotent and safe to re-run.

### Day 7 — Repo hygiene + docs
- Wrote this README.
- Added `.env.example` and `requirements.txt` for reproducibility.
- Next up: the modeled layer and dbt data-quality tests.

### Day 8 — 

### Day 9 — 

### Day 10 — 

### Day 11 — 

### Day 12 — 

### Day 13 — 

### Day 14 — 

### Day 15 — 

### Day 16 — 

### Day 17 — 


### < Today > — < your entry >
-