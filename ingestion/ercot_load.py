import argparse
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

TABLE = "raw.grid_conditions"
COLUMNS = ["ts", "region", "load_mw", "capacity_mw", "wind_mw", "solar_mw"]


def insert_rows(conn, table, columns, rows, conflict=None):
    if not rows:
        return

    query = sql.SQL("INSERT INTO {table} ({columns}) VALUES %s").format(
        table=sql.Identifier(*table.split(".")),
        columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
    )

    if conflict:
        conflict_cols = [conflict] if isinstance(conflict, str) else conflict
        query = sql.SQL("{base} ON CONFLICT ({conflict}) DO NOTHING").format(
            base=query,
            conflict=sql.SQL(", ").join(map(sql.Identifier, conflict_cols)),
        )

    with conn.cursor() as cur:
        execute_values(cur, query, rows)
    conn.commit()


def connect_with_retry(attempts=3, delay_seconds=2):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
            )
            print("Successfully connected to the database!")
            return conn
        except psycopg2.OperationalError as e:
            last_error = e
            print(f"Connection attempt {attempt} failed: {e}")
            if attempt < attempts:
                time.sleep(delay_seconds)
    raise last_error


def fetch_ercot(hours):
    import gridstatus

    iso = gridstatus.Ercot()
    load = iso.get_load("today")  # DataFrame: Time, Load
    fuel = iso.get_fuel_mix("today")  # DataFrame: Time, Wind, Solar, ...

    # gridstatus column names vary by dataset/version - inspect before assuming.
    print("load.columns:", list(load.columns))
    print("fuel.columns:", list(fuel.columns))

    load = load.set_index("Time").resample("5min").mean(numeric_only=True)
    fuel = fuel.set_index("Time").resample("5min").mean(numeric_only=True)

    day_peak_mw = load["Load"].max()

    wind_col = next((c for c in fuel.columns if "wind" in c.lower()), None)
    solar_col = next((c for c in fuel.columns if "solar" in c.lower()), None)

    df = load[["Load"]].join(fuel, how="inner")
    cutoff = df.index.max() - pd.Timedelta(hours=hours)
    df = df[df.index >= cutoff].reset_index()

    df = df.rename(columns={"Time": "ts", "Load": "load_mw"})
    df["region"] = "ERCOT"
    # TODO: gridstatus has ERCOT capacity/reserve datasets - v1 approximates
    # system capacity as 15% headroom over the day's peak load.
    df["capacity_mw"] = day_peak_mw * 1.15
    df["wind_mw"] = df[wind_col] if wind_col else None
    df["solar_mw"] = df[solar_col] if solar_col else None

    return df[COLUMNS]


def fetch_synthetic(hours):
    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=now, periods=hours * 12, freq="5min")

    trough_mw = 38_000
    peak_mw = 68_000
    mean_mw = (trough_mw + peak_mw) / 2
    amplitude_mw = (peak_mw - trough_mw) / 2

    hour_of_day = timestamps.hour + timestamps.minute / 60
    # Cosine peaks at hour 17 (5pm) and troughs 12h later at hour 5 (~4am).
    phase = 2 * np.pi * (hour_of_day - 17) / 24
    load_mw = mean_mw + amplitude_mw * np.cos(phase) + np.random.normal(0, 1500, size=len(timestamps))

    daylight = (hour_of_day > 6) & (hour_of_day < 20)
    solar_mw = np.where(
        daylight,
        np.clip(4000 * np.sin(np.pi * (hour_of_day - 6) / 14) + np.random.normal(0, 300, len(timestamps)), 0, None),
        0,
    )
    wind_mw = np.clip(np.random.normal(6000, 2000, size=len(timestamps)), 0, None)

    return pd.DataFrame({
        "ts": timestamps,
        "region": "ERCOT",
        "load_mw": load_mw,
        "capacity_mw": peak_mw * 1.15,
        "wind_mw": wind_mw,
        "solar_mw": solar_mw,
    })


def to_rows(df):
    rows = []
    for r in df[COLUMNS].to_dict("records"):
        ts = r["ts"]
        rows.append((
            ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
            r["region"],
            float(r["load_mw"]),
            float(r["capacity_mw"]),
            None if pd.isna(r["wind_mw"]) else float(r["wind_mw"]),
            None if pd.isna(r["solar_mw"]) else float(r["solar_mw"]),
        ))
    return rows


def parse_args():
    parser = argparse.ArgumentParser(description="Load ERCOT grid conditions into TimescaleDB")
    parser.add_argument(
        "--source",
        choices=["ercot", "synthetic"],
        default=os.getenv("GRID_SOURCE", "synthetic"),
    )
    parser.add_argument("--hours", type=int, default=24)
    return parser.parse_args()


def main():
    args = parse_args()

    df = fetch_ercot(args.hours) if args.source == "ercot" else fetch_synthetic(args.hours)
    rows = to_rows(df)

    conn = connect_with_retry()
    try:
        insert_rows(conn, TABLE, COLUMNS, rows, conflict=["ts", "region"])
        print(f"Inserted {len(rows)} rows into {TABLE} (source={args.source})")
    finally:
        conn.close()
        print("PostgreSQL connection is safely closed.")


if __name__ == "__main__":
    main()
