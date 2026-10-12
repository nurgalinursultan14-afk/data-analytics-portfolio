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
con = sqlite3.connect(OUT / "internships.db")

results = {}
for f in sorted((HERE / "sql").glob("[0-9][0-9]_*.sql")):
    if f.name.startswith("00_"):
        continue
    df = pd.read_sql_query(f.read_text(), con)
    df.to_csv(OUT / f"{f.stem}.csv", index=False)
    results[f.stem] = df
    print(f"\n=== {f.stem} ===\n{df.to_string(index=False, max_rows=40)}")

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10})
COLORS = {"Software": "#4C72B0", "Data/AI": "#DD8452", "Hardware": "#55A868",
          "Product": "#C44E52", "Quant": "#8172B3"}

# Chart 1: weekly posting pace, stacked by category
wk = results["02_weekly_pace"].pivot(index="week_start", columns="category",
                                     values="new_postings").fillna(0)
wk = wk[[c for c in COLORS if c in wk.columns]]
wk = wk[wk.index < "2026-10-12"]  # drop the partial week of the snapshot
ax = wk.plot(kind="bar", stacked=True, figsize=(10, 4.2), width=0.85,
             color=[COLORS[c] for c in wk.columns])
ax.set_title("New Summer 2027 internship postings per week")
ax.set_xlabel("Week starting")
ax.set_ylabel("New postings")
ax.set_xticklabels([d[5:] for d in wk.index], rotation=90, fontsize=8)
ax.legend(frameon=False, ncol=5, loc="upper left")
plt.tight_layout()
plt.savefig(OUT / "chart_weekly_pace.png")
plt.close()

# Chart 2: how fast postings close
d = results["03_days_open"].set_index("category").sort_values("pct_closed_within_14d")
fig, ax = plt.subplots(figsize=(7.5, 3.8))
cols = ["pct_closed_within_7d", "pct_closed_within_14d", "pct_closed_within_30d"]
labels = ["within 7 days", "within 14 days", "within 30 days"]
for i, (c, lab, col) in enumerate(zip(cols, labels, ["#C44E52", "#DD8452", "#E8C07D"])):
    ax.barh([j + (1 - i) * 0.26 for j in range(len(d))], d[c], height=0.26, color=col, label=lab)
ax.set_yticks(range(len(d)), d.index)
ax.set_xlabel("% of postings already closed")
ax.set_title("Share of Summer 2027 postings closed soon after appearing")
ax.legend(frameon=False, loc="lower right")
plt.tight_layout()
plt.savefig(OUT / "chart_days_open.png")
plt.close()

# Chart 3: top states
st = results["04_locations"].iloc[::-1]
fig, ax = plt.subplots(figsize=(6.5, 4.5))
ax.barh(st["state"], st["postings"], color=["#C44E52" if s == "NY" else "#4C72B0" for s in st["state"]])
ax.set_title("Summer 2027 US internship postings by state (top 15)")
ax.set_xlabel("Distinct postings")
plt.tight_layout()
plt.savefig(OUT / "chart_states.png")
plt.close()

# Chart 4: ATS mix (share on no-account platforms) by category
ats = results["06_ats_mix"]
no_acct = ats[ats["ats"].isin(["Greenhouse", "Lever", "Ashby"])].groupby("category")["pct_of_category"].sum()
wd = ats[ats["ats"] == "Workday"].set_index("category")["pct_of_category"]
mix = pd.DataFrame({"Greenhouse/Lever/Ashby": no_acct, "Workday": wd}).fillna(0).sort_values("Workday")
ax = mix.plot(kind="barh", figsize=(7, 3.6), color=["#55A868", "#8172B3"])
ax.set_xlabel("% of Summer 2027 postings in category")
ax.set_title("About half of postings use Workday (account required)")
ax.set_ylabel("")
ax.legend(frameon=False, loc="lower right")
plt.tight_layout()
plt.savefig(OUT / "chart_ats_mix.png")
plt.close()

print("\nCharts written to", OUT)
