import argparse
import os
import time
from datetime import datetime, timezone

import numpy as np

from ercot_load import connect_with_retry, insert_rows
from weather import CITIES

DEFAULT_TEMP_C = 30.0
TABLE = "raw.meter_telemetry"
COLUMNS = ["ts", "meter_id", "city", "power_kw", "voltage_v"]

LATEST_TEMP_QUERY = """
    SELECT DISTINCT ON (city) city, temperature_c
    FROM raw.weather ORDER BY city, ts DESC;
"""


class Meter:
    def __init__(self, mid, city, rng):
        self.id, self.city = mid, city
        self.online = True
        self.base_kw = rng.uniform(0.5, 1.0)      # fridge, lights, electronics

    def step(self, city_temp_c, rng):
        if not self.online:
            return None
        hvac = max(0.0, (city_temp_c - 24.0)) * rng.uniform(0.25, 0.40)  # AC above 24°C
        spike = rng.uniform(2, 5) if rng.random() < 0.02 else 0.0        # oven/dryer
        power = self.base_kw + hvac + spike + rng.normal(0, 0.05)
        voltage = 240 + rng.normal(0, 1.5)
        return (datetime.now(timezone.utc), self.id, self.city,
                round(power, 3), round(voltage, 1))


def fetch_latest_temps(conn, cities):
    with conn.cursor() as cur:
        cur.execute(LATEST_TEMP_QUERY)
        latest = dict(cur.fetchall())
    return {city: float(latest[city]) if city in latest else DEFAULT_TEMP_C for city in cities}


def build_fleet(fleet_size, cities, rng):
    return [Meter(f"M{i:04d}", str(rng.choice(cities)), rng) for i in range(fleet_size)]


def to_rows(readings):
    return [
        (ts, str(meter_id), str(city), float(power_kw), float(voltage_v))
        for ts, meter_id, city, power_kw, voltage_v in readings
    ]


def run_tick(conn, fleet, cities, rng):
    temps = fetch_latest_temps(conn, cities)
    readings = [meter.step(temps[meter.city], rng) for meter in fleet]
    readings = [r for r in readings if r is not None]

    rows = to_rows(readings)
    insert_rows(conn, TABLE, COLUMNS, rows)
    return len(rows)


def parse_args():
    parser = argparse.ArgumentParser(description="Simulate a smart-meter fleet and stream telemetry into TimescaleDB")
    parser.add_argument("--once", action="store_true", help="run a single batch and exit (for testing)")
    parser.add_argument("--fleet-size", type=int, default=int(os.getenv("FLEET_SIZE", "300")))
    parser.add_argument("--interval", type=float, default=float(os.getenv("TELEMETRY_INTERVAL_SECONDS", "5")))
    return parser.parse_args()


def main():
    args = parse_args()
    rng = np.random.default_rng()
    cities = list(CITIES)
    fleet = build_fleet(args.fleet_size, cities, rng)

    conn = connect_with_retry()
    try:
        while True:
            inserted = run_tick(conn, fleet, cities, rng)
            print(f"Inserted {inserted} readings from {len(fleet)} meters")
            if args.once:
                break
            time.sleep(args.interval)
    finally:
        conn.close()
        print("PostgreSQL connection is safely closed.")


if __name__ == "__main__":
    main()
