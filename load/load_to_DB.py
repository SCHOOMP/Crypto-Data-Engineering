import os
import csv
import glob
from io import StringIO
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    print("ERROR: Missing database settings. Check your .env file.")
    exit()


# COPY-based bulk loader, passed to to_sql as the `method`.
# This streams rows into Postgres via COPY instead of running INSERTs.
def psql_copy(table, conn, keys, data_iter):
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerows(data_iter)
        buffer.seek(0)

        columns = ", ".join(f'"{k}"' for k in keys)
        table_name = f'"{table.schema}"."{table.name}"' if table.schema else f'"{table.name}"'

        sql = f"COPY {table_name} ({columns}) FROM STDIN WITH (FORMAT CSV)"
        cur.copy_expert(sql=sql, file=buffer)


print("Connecting to Postgres...")
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Test connection for real
with engine.connect() as connection:
    print("Engine Connected")

os.chdir('../')

files = glob.glob("data/btc/raw/*.csv", recursive=True)
print("Found", len(files), "files to load")

if not files:
    print("ERROR: No CSV files found. Check the path.")
    exit()

df = pd.read_csv(files[0])

df = df.rename(columns={
    "Timestamp": "ts_epoch",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
})


# Keep only the six columns the table expects
df = df[["ts_epoch", "open", "high", "low", "close", "volume"]]

df.to_sql("bitcoin_raw", engine, if_exists="append", index=False, method=psql_copy)
print("Load complete:", len(df), "rows")