import time
from datetime import datetime, timezone

import requests

from ercot_load import connect_with_retry, insert_rows

CITIES = {
    "Austin":      (30.27, -97.74),
    "Houston":     (29.76, -95.37),
    "Dallas":      (32.78, -96.80),
    "San Antonio": (29.42, -98.49),
    "Midland":     (31.997, -102.078),
}

TABLE = "raw.weather"
COLUMNS = ["ts", "city", "temperature_c", "humidity_pct", "wind_speed_kmh"]

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_city_weather(city, lat, lon, past_days=2):
    resp = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "past_days": past_days,
            "timezone": "UTC",
        },
        timeout=10,
    )
    resp.raise_for_status()
    hourly = resp.json()["hourly"]

    rows = []
    for t, temp, humidity, wind in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["relative_humidity_2m"],
        hourly["wind_speed_10m"],
    ):
        # Open-Meteo returns tz-naive ISO strings even with timezone=UTC;
        # tag them explicitly so downstream joins don't silently misalign.
        ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        rows.append((ts, city, temp, humidity, wind))
    return rows


def main():
    conn = connect_with_retry()
    try:
        total = 0
        for city, (lat, lon) in CITIES.items():
            rows = fetch_city_weather(city, lat, lon)
            insert_rows(conn, TABLE, COLUMNS, rows, conflict=["ts", "city"])
            total += len(rows)
            print(f"{city}: inserted {len(rows)} rows")
            time.sleep(0.5)
        print(f"Done. Inserted {total} rows into {TABLE}")
    finally:
        conn.close()
        print("PostgreSQL connection is safely closed.")


if __name__ == "__main__":
    main()
