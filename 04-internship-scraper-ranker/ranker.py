"""Rank scraped internship postings for one candidate with a transparent, weighted score.

score = 100 * (w_role * role_fit + w_loc * location + w_recency * recency + w_ease * apply_ease)

  role_fit    best keyword weight found in the title, times any penalty factors (0-1)
  location    best score among the posting's locations (NYC 1.0, remote 0.9, ...)
  recency     0.5 ** (age_days / half_life): a posting loses half its recency score every 7 days
  apply_ease  1.0 for no-account systems (Greenhouse, Lever, Ashby), 0.4 otherwise

Postings with excluded flags (no sponsorship, citizens only, closed, grad only) are dropped.
A sensitivity analysis re-ranks under 200 random weight perturbations (±30%) and reports how
stable the top 20 is (Kendall's tau and top-20 overlap).

Usage:  python ranker.py [--profile profile.json] [--top 25]
"""
import argparse
import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

HERE = Path(__file__).parent
US_STATE = re.compile(r",\s*([A-Z]{2})$")
STATES = set("""AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH
NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC""".split())


def role_fit(title, keywords, penalties):
    t = title.lower()
    base = max((w for k, w in keywords.items() if re.search(rf"\b{re.escape(k)}", t)), default=0.0)
    for k, factor in penalties.items():
        if re.search(rf"\b{re.escape(k)}", t):
            base *= factor
    return base


def location_score(locations, p):
    best = 0.0
    for loc in str(locations).split("; "):
        loc = loc.strip()
        if loc in p["location_scores"]:
            s = p["location_scores"][loc]
        elif "remote" in loc.lower() and ("usa" in loc.lower() or loc.lower() == "remote"):
            s = p["location_scores"].get("Remote", 0)
        elif US_STATE.search(loc) and US_STATE.search(loc).group(1) in STATES:   # "London, UK" is not a state
            s = p["location_scores"].get(US_STATE.search(loc).group(1), p["other_us_location_score"])
        elif loc in ("SF", "LA", "United States"):
            s = p["other_us_location_score"]
        else:
            s = p["non_us_location_score"]
        best = max(best, s)
    return best


def score(df, p, weights=None):
    w = weights or p["weights"]
    total = sum(w.values())
    s = (w["role_fit"] * df.role_fit + w["location"] * df.location + w["recency"] * df.recency
         + w["apply_ease"] * df.apply_ease) / total
    return (100 * s).round(1)


def build_features(df, p):
    flags = df["flags"].fillna("")
    keep = ~flags.apply(lambda f: any(x in f.split(";") for x in p["exclude_flags"]))
    keep &= ~df.company.isin(p.get("exclude_companies", []))
    out = df[keep].copy()
    out["role_fit"] = out.title.apply(lambda t: role_fit(t, p["role_keywords"], p["role_penalties"]))
    out["location"] = out.locations.apply(lambda l: location_score(l, p))
    out["recency"] = 0.5 ** (out.age_days.fillna(60) / p["recency_half_life_days"])
    ease = p["apply_ease"]
    out["apply_ease"] = np.where(out.no_account == 1, ease["no_account"], ease["account"])
    return out, int((~keep).sum())


def sensitivity(df, p, top_n=20, runs=200, spread=0.3, seed=0):
    rng = np.random.default_rng(seed)
    base = score(df, p)
    base_top = set(base.nlargest(top_n).index)
    taus, overlaps = [], []
    for _ in range(runs):
        w = {k: v * rng.uniform(1 - spread, 1 + spread) for k, v in p["weights"].items()}
        s = score(df, p, w)
        taus.append(kendalltau(base, s).statistic)
        overlaps.append(len(base_top & set(s.nlargest(top_n).index)) / top_n)
    return {"kendall_tau_mean": round(float(np.mean(taus)), 3),
            "kendall_tau_min": round(float(np.min(taus)), 3),
            f"top{top_n}_overlap_mean": round(float(np.mean(overlaps)), 3),
            f"top{top_n}_overlap_min": round(float(np.min(overlaps)), 3)}


def write_html(top, path, meta):
    rows = "".join(
        f"<tr><td>{i}</td><td>{r.score:.1f}</td><td>{html.escape(r.company)}</td>"
        f"<td><a href='{html.escape(r.url)}'>{html.escape(r.title)}</a></td>"
        f"<td>{html.escape(str(r.locations))}</td><td>{int(r.age_days)}d</td><td>{r.ats}</td>"
        f"<td>{r.role_fit:.2f} / {r.location:.2f} / {r.recency:.2f} / {r.apply_ease:.2f}</td></tr>"
        for i, r in enumerate(top.itertuples(), 1))
    path.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Ranked Internships</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1150px;margin:24px auto;padding:0 16px;color:#222}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border-bottom:1px solid #eee;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#fafafa}}.m{{color:#666}}</style></head><body>
<h1>Top internship matches</h1><p class="m">{html.escape(meta)}</p>
<table><tr><th>#</th><th>Score</th><th>Company</th><th>Role</th><th>Location</th><th>Age</th><th>ATS</th>
<th>Role / Location / Recency / Ease</th></tr>{rows}</table></body></html>""", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=HERE / "profile.json")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()
    p = json.loads(Path(args.profile).read_text())
    raw = pd.read_csv(HERE / "data" / "postings.csv")
    df, dropped = build_features(raw, p)
    df["score"] = score(df, p)
    df = df.sort_values(["score", "age_days"], ascending=[False, True])
    cols = ["score", "company", "title", "locations", "age_days", "ats", "category",
            "role_fit", "location", "recency", "apply_ease", "url"]
    df[cols].to_csv(HERE / "output" / "ranked_postings.csv", index=False)
    sens = sensitivity(df, p)
    meta = (f"{len(raw):,} postings scraped, {dropped:,} excluded by eligibility flags, "
            f"{len(df):,} ranked. Weight sensitivity (200 runs, ±30%): mean Kendall tau "
            f"{sens['kendall_tau_mean']}, mean top-20 overlap {sens['top20_overlap_mean']:.0%}.")
    write_html(df.head(args.top), HERE / "output" / "top_matches.html", meta)
    (HERE / "output" / "sensitivity.json").write_text(json.dumps(sens, indent=2))
    print(meta)
    print(df[cols[:7]].head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()
