"""Run every query in sql/, save results as CSV, and draw the charts used in the README.

Usage:  python build_db.py && python run_analysis.py
"""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "output"
con = sqlite3.connect(OUT / "citibike.db")

results = {}
for f in sorted((HERE / "sql").glob("[0-9][0-9]_*.sql")):
    if f.name.startswith("00_"):
        continue
    df = pd.read_sql_query(f.read_text(), con)
    df.to_csv(OUT / f"{f.stem}.csv", index=False)
    results[f.stem] = df
    print(f"\n=== {f.stem} ===\n{df.to_string(index=False, max_rows=60)}")

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10})
COLORS = {"member": "#4C72B0", "casual": "#DD8452"}

# Chart 1: hourly pattern, weekday vs weekend, member vs casual
hp = results["03_hourly_pattern"]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, day_type in zip(axes, ["weekday", "weekend/holiday"]):
    for who, col in COLORS.items():
        d = hp[(hp.day_type == day_type) & (hp.member_casual == who)]
        ax.plot(d.start_hour, d.pct_of_group, color=col, lw=2, label=who)
    ax.set_title(day_type.capitalize())
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hour ride started")
axes[0].set_ylabel("% of the group's rides")
axes[0].legend(frameon=False)
fig.suptitle("Members have a sharp 8 AM commute peak on weekdays; casual riders mostly do not")
plt.tight_layout()
plt.savefig(OUT / "chart_hourly_pattern.png")
plt.close()

# Chart 2: daily rides, rolling average, rain
dt = results["04_daily_trend"]
fig, ax = plt.subplots(figsize=(10, 4))
wet = dt.precip_in >= 0.10
ax.bar(dt.date.str[5:], dt.rides / 1000, color=["#6A9FD4" if w else "#C9D3DE" for w in wet])
ax.plot(dt.date.str[5:], dt.rolling_7d_avg / 1000, color="#333333", lw=1.8, label="7-day rolling average")
ax.set_ylabel("Rides (thousands)")
ax.set_title("Daily Citi Bike rides, September 2026 (blue = 0.10 in or more of rain)")
ax.tick_params(axis="x", rotation=90, labelsize=8)
ax.legend(frameon=False, loc="lower left")
plt.tight_layout()
plt.savefig(OUT / "chart_daily_rain.png")
plt.close()

# Chart 3: morning-rush net flow for every station (same logic as 06, without the top-10 cut)
flows = pd.read_sql_query("""
    WITH am AS (
        SELECT * FROM rides
        WHERE start_hour BETWEEN 7 AND 9
          AND strftime('%w', start_date) NOT IN ('0', '6') AND start_date <> '2026-09-07'
    ),
    f AS (
        SELECT station_id, SUM(d) AS departures, SUM(a) AS arrivals FROM (
            SELECT start_station_id AS station_id, 1 AS d, 0 AS a FROM am WHERE start_station_id IS NOT NULL
            UNION ALL
            SELECT end_station_id, 0, 1 FROM am WHERE end_station_id IS NOT NULL)
        GROUP BY station_id
    )
    SELECT s.lat, s.lng, (f.arrivals - f.departures) * 1.0 /
           (SELECT COUNT(DISTINCT start_date) FROM am) AS net_per_morning
    FROM f JOIN stations s USING (station_id)
""", con)
flows = flows.sort_values("net_per_morning", key=abs)
fig, ax = plt.subplots(figsize=(6.5, 7.5))
sc = ax.scatter(flows.lng, flows.lat, c=flows.net_per_morning.clip(-30, 30), cmap="RdBu",
                s=6 + flows.net_per_morning.abs().clip(0, 40), vmin=-30, vmax=30, linewidths=0)
plt.colorbar(sc, ax=ax, shrink=0.6, label="Net bikes per morning (arrivals - departures)")
ax.set_aspect(1 / 0.76)  # roughly equal-distance axes at NYC's latitude
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Weekday 7-10 AM: red stations empty out, blue stations fill up")
plt.tight_layout()
plt.savefig(OUT / "chart_station_imbalance.png")
plt.close()

# Chart 4: e-bike share by distance
eb = results["08_ebike_by_distance"]
fig, ax = plt.subplots(figsize=(6.5, 3.6))
ax.bar(eb.distance_band.str[3:], eb.pct_ebike, color="#55A868")
for i, v in enumerate(eb.pct_ebike):
    ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
ax.set_ylim(0, 100)
ax.set_ylabel("% of rides on an e-bike")
ax.set_xlabel("Straight-line trip distance")
ax.set_title("The longer the trip, the more likely it is on an e-bike")
plt.tight_layout()
plt.savefig(OUT / "chart_ebike_distance.png")
plt.close()

print("\nCharts saved to", OUT)
