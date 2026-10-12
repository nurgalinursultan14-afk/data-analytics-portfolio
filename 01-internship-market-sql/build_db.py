"""Build a normalized SQLite database from the SimplifyJobs listings snapshot.

Usage:  python build_db.py            -> creates output/internships.db
"""
import csv
import gzip
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "data" / "listings_2026-10-12.json.gz"
DB = HERE / "output" / "internships.db"

# The source mixes old and new category labels; map them to five buckets.
CATEGORY_MAP = {
    "Software": "Software", "Software Engineering": "Software",
    "AI/ML/Data": "Data/AI", "Data Science, AI & Machine Learning": "Data/AI",
    "Hardware": "Hardware", "Hardware Engineering": "Hardware",
    "Product": "Product", "Product Management": "Product",
    "Quant": "Quant", "Quantitative Finance": "Quant",
}

US_STATES = set("""AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS
MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC""".split())
CITY_ALIASES = {"NYC": "NY", "SF": "CA", "LA": "CA"}


def ats_of(url: str) -> str:
    """Classify the applicant-tracking system from the apply URL."""
    u = (url or "").lower()
    rules = [("greenhouse.io", "Greenhouse"), ("ashbyhq.com", "Ashby"), ("lever.co", "Lever"),
             ("myworkdayjobs.com", "Workday"), ("oraclecloud.com", "Oracle"), ("icims.com", "iCIMS"),
             ("smartrecruiters.com", "SmartRecruiters"), ("successfactors", "SuccessFactors"),
             ("workable.com", "Workable"), ("rippling.com", "Rippling"), ("jobvite.com", "Jobvite"),
             ("eightfold.ai", "Eightfold"), ("taleo.net", "Taleo")]
    for key, name in rules:
        if key in u:
            return name
    return "Company site / other"


def parse_location(loc: str):
    """Return (state, country, is_remote) for one location string."""
    loc = loc.strip()
    is_remote = int("remote" in loc.lower())
    if loc in CITY_ALIASES:
        return CITY_ALIASES[loc], "US", is_remote
    if loc in ("United States", "Remote in USA", "Remote"):
        return None, "US", is_remote
    m = re.search(r",\s*([A-Z]{2})$", loc)
    if m and m.group(1) in US_STATES:
        return m.group(1), "US", is_remote
    if "Canada" in loc:
        return None, "Canada", is_remote
    if "UK" in loc:
        return None, "UK", is_remote
    return None, "Other", is_remote


def to_date(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else None


def main():
    rows = json.load(gzip.open(SRC, "rt", encoding="utf-8"))
    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript((HERE / "sql" / "00_schema.sql").read_text())

    for r in rows:
        if not r.get("is_visible", True):
            continue
        con.execute(
            "INSERT INTO postings VALUES (?,?,?,?,?,?,?,?,?,?)",
            (r["id"], r["company_name"].strip(), r["title"].strip(),
             CATEGORY_MAP.get(r["category"], "Other"), int(bool(r["active"])),
             to_date(r["date_posted"]), to_date(r["date_updated"]),
             r.get("sponsorship") or "Other", ats_of(r["url"]), r["url"]))
        for t in r.get("terms") or []:
            con.execute("INSERT INTO posting_terms VALUES (?,?)", (r["id"], t))
        for loc in r.get("locations") or []:
            state, country, remote = parse_location(loc)
            con.execute("INSERT INTO posting_locations VALUES (?,?,?,?,?)",
                        (r["id"], loc, state, country, remote))
        for d in r.get("degrees") or []:
            con.execute("INSERT INTO posting_degrees VALUES (?,?)", (r["id"], d))
    with (HERE / "data" / "status_history.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            con.execute("INSERT INTO status_history VALUES (?,?,?)",
                        (r["id"], r["first_seen"], r["first_closed"] or None))
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
    print(f"Loaded {n:,} postings into {DB.name}")
    con.close()


if __name__ == "__main__":
    main()
