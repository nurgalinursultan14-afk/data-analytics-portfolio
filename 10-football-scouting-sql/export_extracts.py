"""Export tidy, Tableau-ready extracts of the scouting pool from output/scouting.db.

Usage:
    python build_db.py          # once, builds output/scouting.db
    python export_extracts.py   # -> tableau/players.csv, tableau/shots.csv
"""
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DB = HERE / "output" / "scouting.db"
OUT = HERE / "tableau"

# One row per player in the pool: per-90 metrics, percentiles, score and the club's finish.
PLAYERS_SQL = """
WITH table_pos AS (
    SELECT team,
           RANK() OVER (ORDER BY SUM(CASE WHEN gf > ga THEN 3 WHEN gf = ga THEN 1 ELSE 0 END) DESC,
                                 SUM(gf - ga) DESC) AS club_finish
    FROM (SELECT home_team AS team, home_score AS gf, away_score AS ga FROM matches
          UNION ALL SELECT away_team, away_score, home_score FROM matches)
    GROUP BY team
)
SELECT RANK() OVER (ORDER BY s.score DESC) AS score_rank,
       s.player_id, s.player, s.team, t.club_finish,
       CASE WHEN t.club_finish <= 6 THEN 'Top six' ELSE '7th or lower' END AS club_tier,
       s.matches, CAST(ROUND(s.minutes) AS INTEGER) AS minutes,
       s.score,
       s.np_xg_90, s.xa_90, s.key_passes_90, s.dribbles_won_90, s.prog_carries_90, s.box_passes_90,
       s.p_np_xg, s.p_xa, s.p_key_passes, s.p_dribbles, s.p_prog_carries, s.p_box_passes,
       s.np_goals, s.assists, s.np_xg, s.xa
FROM wide_forward_scores s
JOIN table_pos t ON t.team = s.team
ORDER BY s.score DESC
"""

# One row per non-penalty shot by a pool player, for a shot map (x, y on a 120 x 80 pitch).
SHOTS_SQL = """
SELECT e.player_id, e.player, e.team, e.match_id, m.match_date, e.minute,
       e.x, e.y, ROUND(e.xg, 3) AS xg, e.outcome,
       CASE WHEN e.outcome = 'Goal' THEN 1 ELSE 0 END AS is_goal
FROM events e
JOIN wide_forwards w ON w.player_id = e.player_id AND w.team = e.team
JOIN matches m ON m.match_id = e.match_id
WHERE e.type = 'Shot' AND e.shot_type <> 'Penalty'
ORDER BY e.player, m.match_date, e.minute
"""


def main():
    if not DB.exists():
        raise SystemExit(f"{DB} not found. Run build_db.py first.")
    OUT.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    players = pd.read_sql(PLAYERS_SQL, con)
    shots = pd.read_sql(SHOTS_SQL, con)
    players.to_csv(OUT / "players.csv", index=False)
    shots.to_csv(OUT / "shots.csv", index=False)

    # Sanity checks against run_analysis.py's published numbers
    print(f"players.csv: {len(players)} players, top: {players.player[0]} ({players.score[0]})")
    by_player = shots.groupby("player_id").agg(goals=("is_goal", "sum"), xg=("xg", "sum"))
    check = players.set_index("player_id")[["np_goals", "np_xg"]].join(by_player)
    assert (check.goals == check.np_goals).all(), "shot goals don't match np_goals"
    assert ((check.xg - check.np_xg).abs() <= 0.06).all(), "shot xG doesn't match np_xg"
    print(f"shots.csv: {len(shots):,} non-penalty shots, {shots.is_goal.sum()} goals "
          f"(match the pool's np_goals and np_xg)")


if __name__ == "__main__":
    main()
