"""Derive when each posting was first seen and first marked closed, from the repo's git history.

The SimplifyJobs repo commits its listings.json every ~30 minutes. This script takes one
snapshot every 3 days (Jun 15 - Oct 12, 2026) and records, per posting:
    first_seen    - first snapshot date the posting appears in
    first_closed  - first snapshot date it appears with active = false (blank if still open)

Usage (needs git and ~300 MB of transfer):
    git clone --filter=blob:none --no-checkout https://github.com/SimplifyJobs/Summer2027-Internships.git repo
    python extract_history.py repo
Output: data/status_history.csv  (already included, so you only need this to refresh it)
"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
START, STEP_DAYS = date(2026, 6, 15), 3
PATH_IN_REPO = ".github/scripts/listings.json"


def pick_snapshots(repo):
    log = subprocess.run(["git", "-C", repo, "log", "--format=%H %cs", f"--since={START}",
                          "--", PATH_IN_REPO], capture_output=True, text=True, check=True).stdout
    picks = {}
    for line in reversed(log.split("\n")):
        if not line:
            continue
        sha, day = line.split()
        bucket = (date.fromisoformat(day) - START).days // STEP_DAYS
        picks.setdefault(bucket, (sha, day))  # earliest commit in each 3-day bucket
    return sorted(picks.values(), key=lambda x: x[1])


def main(repo):
    first_seen, first_closed = {}, {}
    for sha, day in pick_snapshots(repo):
        blob = subprocess.run(["git", "-C", repo, "show", f"{sha}:{PATH_IN_REPO}"],
                              capture_output=True, check=True).stdout
        for x in json.loads(blob):
            first_seen.setdefault(x["id"], day)
            if not x.get("active") and x["id"] not in first_closed:
                first_closed[x["id"]] = day
        print("processed", day)
    out = HERE / "data" / "status_history.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "first_seen", "first_closed"])
        for pid, seen in sorted(first_seen.items()):
            w.writerow([pid, seen, first_closed.get(pid, "")])
    print(f"wrote {len(first_seen):,} rows to {out}")


if __name__ == "__main__":
    main(sys.argv[1])
