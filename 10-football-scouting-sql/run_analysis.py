"""Run every query in sql/, save results as CSV, draw the README charts and test the score.

Usage:  python build_db.py && python run_analysis.py
"""
import json
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kendalltau

HERE = Path(__file__).parent
OUT = HERE / "output"
con = sqlite3.connect(OUT / "scouting.db")

results = {}
for f in sorted((HERE / "sql").glob("[0-9][0-9]_*.sql")):
    if f.name.startswith("00_"):
        continue
    df = pd.read_sql_query(f.read_text(), con)
    df.to_csv(OUT / f"{f.stem}.csv", index=False)
    results[f.stem] = df
    print(f"\n=== {f.stem} ===\n{df.to_string(index=False, max_rows=40)}")

pool = pd.read_sql_query("SELECT * FROM wide_forward_scores", con)
PCTS = ["p_np_xg", "p_xa", "p_key_passes", "p_dribbles", "p_prog_carries", "p_box_passes"]

# Robustness: change every weight by up to +/-30% at random, 1,000 times, and see how much
# the ranking and the top 10 move compared with equal weights.
rng = np.random.default_rng(10)
base = pool[PCTS].mean(axis=1)
base_top = set(pool.loc[base.nlargest(10).index, "player"])
taus, overlaps, in_top = [], [], {p: 0 for p in base_top}
for _ in range(1000):
    w = rng.uniform(0.7, 1.3, len(PCTS))
    s = (pool[PCTS] * w).sum(axis=1) / w.sum()
    taus.append(kendalltau(base, s).statistic)
    top_now = set(pool.loc[s.nlargest(10).index, "player"])
    overlaps.append(len(base_top & top_now))
    for p in base_top & top_now:
        in_top[p] += 1
robust = {
    "pool_size": int(len(pool)),
    "kendall_tau_median": round(float(np.median(taus)), 3),
    "kendall_tau_min": round(float(np.min(taus)), 3),
    "top10_overlap_median": int(np.median(overlaps)),
    "top10_overlap_min": int(np.min(overlaps)),
    "always_top10": sorted(p for p, n in in_top.items() if n == 1000),
}
print("\n=== robustness ===\n", json.dumps(robust, indent=2))

summary = {
    "data_quality": dict(zip(results["01_data_quality"].check_name, results["01_data_quality"].value)),
    "top10": results["03_wide_forward_shortlist"][["rank", "player", "team", "score"]].to_dict("records"),
    "outside_top_six": results["04_outside_top_six"][["rank", "player", "team", "club_finish", "score"]].to_dict("records"),
    "robustness": robust,
}
(OUT / "results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float))

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10})

# StatsBomb stores full legal names; charts use the names fans know. Labels only: the CSVs
# keep StatsBomb's names so they join back to the data.
KNOWN_AS = {
    "Alexis Alejandro Sánchez Sánchez": "Alexis Sánchez", "Kevin De Bruyne": "De Bruyne",
    "Philippe Coutinho Correia": "Coutinho", "Gerard Deulofeu Lázaro": "Deulofeu",
    "Willian Borges da Silva": "Willian", "Pedro Eliezer Rodríguez Ledesma": "Pedro",
    "Juan Manuel Mata García": "Mata", "Yannick Bolasie Yala": "Bolasie",
    "Carles Gil de Pareja Vicent": "Carles Gil",
}


def short(name):
    """Chart label: the known name, else the last word ('Riyad Mahrez' -> 'Mahrez')."""
    return KNOWN_AS.get(name, name.split()[-1])

# Chart 1: the top 10 by score, split into the six percentiles' contributions.
top = pool.sort_values("score", ascending=False).head(10).iloc[::-1]
labels = {"p_np_xg": "Shooting (np xG)", "p_xa": "Chance creation (xA)", "p_key_passes": "Key passes",
          "p_dribbles": "Dribbles won", "p_prog_carries": "Progressive carries", "p_box_passes": "Passes into box"}
colors = ["#2F5D8C", "#5B8DB8", "#A9C3E0", "#DD8452", "#F2B880", "#8C8C8C"]
fig, ax = plt.subplots(figsize=(9, 4.6))
left = np.zeros(len(top))
for c, col in zip(PCTS, colors):
    vals = top[c].to_numpy() / 6
    ax.barh([f"{short(p)} ({t})" for p, t in zip(top.player, top.team)], vals, left=left, color=col, label=labels[c])
    left += vals
for i, v in enumerate(top.score):
    ax.text(v + 0.8, i, f"{v:.0f}", va="center", fontsize=9)
ax.set_xlim(0, 100)
ax.set_xlabel("Scouting score (average percentile within the pool)")
ax.set_title(f"Top 10 of {len(pool)} Premier League wide forwards, 2015/16")
ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.14))
plt.tight_layout()
plt.savefig(OUT / "chart_top10.png")
plt.close()

# Chart 2: shooting vs creating, every player in the pool, top 10 labelled.
fig, ax = plt.subplots(figsize=(7.5, 5))
is_top = pool.player.isin(top.player)
ax.scatter(pool.np_xg_90[~is_top], pool.xa_90[~is_top], s=28, color="#B8C4D0", label="Rest of the pool")
ax.scatter(pool.np_xg_90[is_top], pool.xa_90[is_top], s=40, color="#2F5D8C", label="Top 10 by score")
for _, r in pool[is_top].iterrows():
    ax.annotate(short(r.player), (r.np_xg_90, r.xa_90), xytext=(4, 3), textcoords="offset points", fontsize=8)
ax.axvline(pool.np_xg_90.median(), color="#999", lw=0.8, ls="--")
ax.axhline(pool.xa_90.median(), color="#999", lw=0.8, ls="--")
ax.set_xlabel("Non-penalty xG per 90 (own shots)")
ax.set_ylabel("xA per 90 (shots they set up)")
ax.set_title("Shooters vs creators (dashed lines: pool medians)")
ax.legend(frameon=False, fontsize=8, loc="upper right")
plt.tight_layout()
plt.savefig(OUT / "chart_shoot_vs_create.png")
plt.close()

print("\nSaved CSVs, results.json and 2 charts to output/")
