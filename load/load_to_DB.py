import os
import csv
import glob
from io import StringIO
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    print("ERROR: Missing database settings. Check your .env file.")
    exit()
print("[1/8] Env loaded OK")


# COPY-based bulk loader, passed to to_sql as the `method`.
def psql_copy(table, conn, keys, data_iter):
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        buffer = StringIO()
        writer = csv.writer(buffer)
        rows = list(data_iter)          # materialize so we can count them
        writer.writerows(rows)
        buffer.seek(0)

        columns = ", ".join(f'"{k}"' for k in keys)
        table_name = f'"{table.schema}"."{table.name}"' if table.schema else f'"{table.name}"'

        sql = f"COPY {table_name} ({columns}) FROM STDIN WITH (FORMAT CSV)"
        cur.copy_expert(sql=sql, file=buffer)
        print(f"      COPY sent {len(rows)} rows -> {table.name}")


print("[2/8] Connecting to Postgres...")
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

with engine.connect() as connection:
    print("[3/8] Engine connected OK")

os.chdir('../')

files = glob.glob("data/btc/raw/*.csv", recursive=True)
print(f"[4/8] Found {len(files)} file(s) to load")

if not files:
    print("ERROR: No CSV files found. Check the path.")
    exit()

df = pd.read_csv(files[0])
print(f"[5/8] Read CSV: {len(df)} rows, columns = {list(df.columns)}")

df = df.rename(columns={
    "Timestamp": "ts_epoch",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
})

# Keep only the six columns the table expects
staging_cols = ["ts_epoch", "open", "high", "low", "close", "volume"]
df = df[staging_cols]
print(f"[6/8] After rename/select, columns = {list(df.columns)}")
print("       Sample row:")
print(df.head(3).to_string(index=False))

# idempotent load: COPY into staging, then merge into bitcoin_raw
with engine.begin() as conn:
    print("[7/8] Building staging table...")
    conn.exec_driver_sql("DROP TABLE IF EXISTS staging_bitcoin;")
    conn.exec_driver_sql("""
        CREATE TABLE staging_bitcoin (
            ts_epoch BIGINT,
            open     NUMERIC(18,8),
            high     NUMERIC(18,8),
            low      NUMERIC(18,8),
            close    NUMERIC(18,8),
            volume   NUMERIC(24,8)
        );
    """)
    print("       staging_bitcoin created")

    before = conn.execute(text("SELECT count(*) FROM bitcoin_raw;")).scalar()
    print(f"       bitcoin_raw count BEFORE: {before}")

    # fast COPY into the constraint-free staging table
    print("       COPYing into staging...")
    df.to_sql("staging_bitcoin", conn, if_exists="append",
              index=False, method=psql_copy)

    staged = conn.execute(text("SELECT count(*) FROM staging_bitcoin;")).scalar()
    print(f"       staging_bitcoin count: {staged}")

    # merge: skip any timestamp already present in bitcoin_raw
    print("       Merging staging -> bitcoin_raw (ON CONFLICT DO NOTHING)...")
    conn.exec_driver_sql("""
        INSERT INTO bitcoin_raw (ts_epoch, open, high, low, close, volume)
        SELECT ts_epoch, open, high, low, close, volume
        FROM staging_bitcoin
        ON CONFLICT (ts_epoch) DO NOTHING;
    """)

    after = conn.execute(text("SELECT count(*) FROM bitcoin_raw;")).scalar()
    print(f"       bitcoin_raw count AFTER:  {after}")

print(f"[8/8] DONE  bitcoin_raw: {before} -> {after} rows (+{after - before} new)")