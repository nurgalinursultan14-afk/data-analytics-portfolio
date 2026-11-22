"""Build a SQLite database of every Premier League 2015/16 match from StatsBomb Open Data.

Usage:  python build_db.py            -> downloads the JSON if needed, creates output/scouting.db

Data: StatsBomb Open Data (https://github.com/statsbomb/open-data), free for non-commercial
use under StatsBomb's terms; any published work must credit StatsBomb as the source.
The raw JSON (about 1.2 GB for 380 matches) is cached in data/ and git-ignored.

Python only flattens the nested JSON into all-text staging tables, one row per lineup spell
and one row per event of the types this project uses. sql/00_schema.sql does the typing,
cleaning and minutes logic in SQL.
"""
import json
import sqlite3
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
DB = HERE / "output" / "scouting.db"
BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/"
COMPETITION_ID, SEASON_ID = 2, 27          # Premier League, 2015/2016

# Event types kept; everything else (pressure, ball receipt, duels...) is not needed here.
KEEP = {"Shot", "Pass", "Carry", "Dribble", "Ball Recovery", "Interception"}


def fetch(rel):
    """Download one file into data/ unless it is already cached; return the parsed JSON."""
    path = DATA / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(BASE_URL + rel, tmp)
        tmp.rename(path)
    return json.loads(path.read_text(encoding="utf-8"))


def loc(e, key="location"):
    v = e.get(key)
    return (v[0], v[1]) if isinstance(v, list) and len(v) >= 2 else (None, None)


def event_row(match_id, e):
    t = e["type"]["name"]
    x, y = loc(e)
    end_x = end_y = outcome = xg = shot_type = key_pass_id = None
    shot_assist = goal_assist = cross = 0
    if t == "Pass":
        p = e["pass"]
        end_x, end_y = loc(p, "end_location")
        outcome = (p.get("outcome") or {}).get("name")      # missing = completed
        shot_assist = int(bool(p.get("shot_assist")))
        goal_assist = int(bool(p.get("goal_assist")))
        cross = int(bool(p.get("cross")))
    elif t == "Carry":
        end_x, end_y = loc(e["carry"], "end_location")
    elif t == "Shot":
        s = e["shot"]
        end_x, end_y = loc(s, "end_location")[:2]
        outcome = s["outcome"]["name"]
        xg = s.get("statsbomb_xg")
        shot_type = s["type"]["name"]
        key_pass_id = s.get("key_pass_id")
    elif t == "Dribble":
        outcome = e["dribble"]["outcome"]["name"]
    elif t == "Interception":
        outcome = e["interception"]["outcome"]["name"]
    player = e.get("player") or {}
    return (e["id"], match_id, e["period"], e["minute"], e["second"], t,
            e["team"]["name"], player.get("id"), player.get("name"),
            x, y, end_x, end_y, outcome, xg, shot_type, key_pass_id,
            shot_assist, goal_assist, cross)


def load_match(match_id):
    events = fetch(f"events/{match_id}.json")
    lineups = fetch(f"lineups/{match_id}.json")
    ev = [event_row(match_id, e) for e in events if e["type"]["name"] in KEEP]
    # Last minute of play in each period, so an open-ended spell ("to": null) gets an end.
    period_end = {}
    for e in events:
        period_end[e["period"]] = max(period_end.get(e["period"], 0), e["minute"] + e["second"] / 60)
    spells = []
    for team in lineups:
        for p in team["lineup"]:
            for pos in p.get("positions", []):
                spells.append((match_id, team["team_name"], p["player_id"], p["player_name"],
                               pos["position"], pos["from"], pos.get("to"), pos["from_period"],
                               pos.get("to_period")))
    ends = [(match_id, k, v) for k, v in period_end.items()]
    return ev, spells, ends


def main():
    matches = fetch(f"matches/{COMPETITION_ID}/{SEASON_ID}.json")
    DB.parent.mkdir(exist_ok=True)
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript("""
        CREATE TABLE raw_matches (match_id, match_date, home_team, away_team, home_score, away_score);
        CREATE TABLE raw_events (event_id, match_id, period, minute, second, type, team,
            player_id, player, x, y, end_x, end_y, outcome, xg, shot_type, key_pass_id,
            shot_assist, goal_assist, is_cross);
        CREATE TABLE raw_spells (match_id, team, player_id, player, position,
            from_clock, to_clock, from_period, to_period);
        CREATE TABLE raw_period_end (match_id, period, last_minute);
    """)
    con.executemany("INSERT INTO raw_matches VALUES (?,?,?,?,?,?)", [
        (m["match_id"], m["match_date"], m["home_team"]["home_team_name"],
         m["away_team"]["away_team_name"], m["home_score"], m["away_score"]) for m in matches])
    ids = [m["match_id"] for m in matches]
    print(f"Loading {len(ids)} matches (downloads are cached in data/) ...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, (ev, spells, ends) in enumerate(pool.map(load_match, ids), 1):
            con.executemany(f"INSERT INTO raw_events VALUES ({','.join('?' * 20)})", ev)
            con.executemany("INSERT INTO raw_spells VALUES (?,?,?,?,?,?,?,?,?)", spells)
            con.executemany("INSERT INTO raw_period_end VALUES (?,?,?)", ends)
            if i % 50 == 0:
                print(f"  {i}/{len(ids)}")
    con.executescript((HERE / "sql" / "00_schema.sql").read_text())
    con.commit()
    con.execute("VACUUM")
    for t in ("matches", "events", "player_minutes"):
        print(f"{t}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:,} rows")
    con.close()


if __name__ == "__main__":
    main()
