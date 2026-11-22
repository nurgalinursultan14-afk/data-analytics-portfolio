"""Python prototype of the Tableau scouting dashboard's layout, from the tableau/ extracts.

Usage:  python export_extracts.py && python prototype.py   # -> output/prototype.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
players = pd.read_csv(HERE / "tableau" / "players.csv")
shots = pd.read_csv(HERE / "tableau" / "shots.csv")

KNOWN_AS = {
    "Alexis Alejandro Sánchez Sánchez": "Alexis Sánchez", "Kevin De Bruyne": "De Bruyne",
    "Philippe Coutinho Correia": "Coutinho", "Gerard Deulofeu Lázaro": "Deulofeu",
    "Willian Borges da Silva": "Willian", "Pedro Eliezer Rodríguez Ledesma": "Pedro",
}


def short(name):
    return KNOWN_AS.get(name, name.split()[-1])


# The player the dashboard opens on: the best-scoring player at a club outside the top six.
focus = players[players.club_tier == "7th or lower"].iloc[0]
TOP, OTHER = "#2F5D8C", "#DD8452"

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 9})
fig = plt.figure(figsize=(13, 7.2))
grid = fig.add_gridspec(2, 3, height_ratios=[0.22, 1], hspace=0.35, wspace=0.35)
fig.suptitle("Wide forward scouting · Premier League 2015/16 (prototype of the Tableau dashboard)",
             fontsize=12, x=0.02, ha="left")

# KPI tiles for the selected player.
kpis = [("Scouting score", f"{focus.score:.1f}", f"rank {focus.score_rank} of {len(players)}"),
        ("Non-penalty goals / xG", f"{focus.np_goals} / {focus.np_xg}", "own shots"),
        ("Assists / xA", f"{focus.assists} / {focus.xa}", "shots set up")]
for i, (title, value, sub) in enumerate(kpis):
    ax = fig.add_subplot(grid[0, i])
    ax.axis("off")
    ax.text(0, 0.85, title, fontsize=9, color="#5B6472", transform=ax.transAxes)
    ax.text(0, 0.25, value, fontsize=20, fontweight="bold", transform=ax.transAxes)
    ax.text(0, -0.05, f"{short(focus.player)} · {focus.team} · {sub}", fontsize=8, color="#5B6472",
            transform=ax.transAxes)

# 1. Shortlist: top 12 by score, coloured by club tier.
ax = fig.add_subplot(grid[1, 0])
top = players.head(12).iloc[::-1]
ax.barh([short(p) for p in top.player], top.score,
        color=[TOP if t == "Top six" else OTHER for t in top.club_tier])
ax.set_xlim(0, 100)
ax.set_title("Shortlist by score", loc="left", fontsize=10)
ax.set_xlabel("Scouting score")
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=TOP), plt.Rectangle((0, 0), 1, 1, color=OTHER)],
          labels=["Top-six club", "7th or lower"], frameon=False, fontsize=8, ncol=2,
          loc="upper center", bbox_to_anchor=(0.5, -0.12))

# 2. Percentile profile of the selected player.
ax = fig.add_subplot(grid[1, 1])
metrics = [("p_np_xg", "Shooting (np xG)"), ("p_xa", "Chance creation (xA)"), ("p_key_passes", "Key passes"),
           ("p_dribbles", "Dribbles won"), ("p_prog_carries", "Progressive carries"),
           ("p_box_passes", "Passes into box")][::-1]
ax.barh([m[1] for m in metrics], [focus[m[0]] for m in metrics], color=OTHER)
ax.axvline(50, color="#999", lw=0.8, ls="--")
ax.set_xlim(0, 100)
ax.set_title(f"{short(focus.player)}: percentile in the pool", loc="left", fontsize=10)
ax.set_xlabel("Percentile (dashed line = pool median)")

# 3. Shot map of the selected player on the attacking half (StatsBomb 120 x 80 pitch).
ax = fig.add_subplot(grid[1, 2])
for xs, ys in [([60, 120, 120, 60, 60], [0, 0, 80, 80, 0]),        # half pitch
               ([120, 102, 102, 120], [18, 18, 62, 62]),            # penalty area
               ([120, 114, 114, 120], [30, 30, 50, 50])]:           # six-yard box
    ax.plot(ys, xs, color="#C9CED6", lw=1)
mine = shots[shots.player_id == focus.player_id]
goals = mine[mine.is_goal == 1]
ax.scatter(mine.y, mine.x, s=mine.xg * 600 + 10, facecolors="none", edgecolors="#8C8C8C", lw=0.8)
ax.scatter(goals.y, goals.x, s=goals.xg * 600 + 10, color=OTHER, label=f"Goal ({len(goals)})")
ax.set_xlim(-2, 82)
ax.set_ylim(58, 122)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title(f"{short(focus.player)}: {len(mine)} non-penalty shots (size = xG)", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="lower center")

plt.savefig(HERE / "output" / "prototype.png", bbox_inches="tight")
print(f"Saved output/prototype.png (focus: {focus.player})")
