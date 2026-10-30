"""Build a SQLite star schema from one month of Citi Bike trips plus NOAA daily weather.

Usage:  python build_db.py            -> downloads the trip file if needed, creates output/citibike.db
"""
import csv
import io
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
MONTH = "202609"
TRIPS_ZIP = HERE / "data" / f"{MONTH}-citibike-tripdata.zip"
TRIPS_URL = f"https://s3.amazonaws.com/tripdata/{MONTH}-citibike-tripdata.zip"
WEATHER = HERE / "data" / "ghcn_central_park_2026.csv"
DB = HERE / "output" / "citibike.db"

TRIP_COLS = ["ride_id", "rideable_type", "started_at", "ended_at", "start_station_name",
             "start_station_id", "end_station_name", "end_station_id", "start_lat", "start_lng",
             "end_lat", "end_lng", "member_casual"]


def download():
    if TRIPS_ZIP.exists():
        return
    print(f"Downloading {TRIPS_URL} (~1 GB) ...")
    urllib.request.urlretrieve(TRIPS_URL, TRIPS_ZIP)


def load_raw(con):
    """Stage the raw CSVs as all-text tables; 00_schema.sql does the cleaning in SQL."""
    con.execute(f"CREATE TABLE raw_trips ({', '.join(c + ' TEXT' for c in TRIP_COLS)})")
    insert = f"INSERT INTO raw_trips VALUES ({', '.join('?' * len(TRIP_COLS))})"
    n = 0
    with zipfile.ZipFile(TRIPS_ZIP) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".csv"):
                continue
            with z.open(name) as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
                rows = ([r[c] for c in TRIP_COLS] for r in reader)
                cur = con.executemany(insert, rows)
                n += cur.rowcount
            print(f"  loaded {name}  (running total {n:,})")

    con.execute("CREATE TABLE raw_weather (station TEXT, date TEXT, element TEXT, value INTEGER,"
                " m_flag TEXT, q_flag TEXT, s_flag TEXT, obs_time TEXT)")
    with open(WEATHER, newline="") as f:
        reader = csv.reader(f)
        next(reader)
        con.executemany("INSERT INTO raw_weather VALUES (?,?,?,?,?,?,?,?)", reader)


def main():
    download()
    DB.parent.mkdir(exist_ok=True)
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode = OFF")
    con.execute("PRAGMA synchronous = OFF")
    load_raw(con)
    con.executescript((HERE / "sql" / "00_schema.sql").read_text())
    con.commit()
    con.execute("VACUUM")
    for t in ("trips", "stations", "weather_daily"):
        print(f"{t}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:,} rows")
    con.close()


if __name__ == "__main__":
    main()
