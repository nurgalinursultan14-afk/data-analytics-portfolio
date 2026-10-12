"""Scrape the SimplifyJobs Summer 2027 internship README into a clean table.

The README is an HTML table per job category. Rows starting with "↳" belong to the company
in the row above; multi-city postings hide their cities in a <details> block; flags in the
title (🛂 no sponsorship, 🇺🇸 citizens only, 🔒 closed, 🎓 grad only) carry eligibility info.

Usage:  python scraper.py            -> data/postings.csv (one row per posting)
        python scraper.py --cached   -> parse data/README.md without downloading again
"""
import argparse
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md"
HERE = Path(__file__).parent
FLAGS = {"🛂": "no_sponsorship", "🇺🇸": "citizens_only", "🔒": "closed", "🎓": "grad_only"}
ATS_RULES = [("greenhouse.io", "Greenhouse"), ("ashbyhq.com", "Ashby"), ("lever.co", "Lever"),
             ("myworkdayjobs.com", "Workday"), ("oraclecloud.com", "Oracle"), ("icims.com", "iCIMS"),
             ("smartrecruiters.com", "SmartRecruiters"), ("successfactors", "SuccessFactors")]
NO_ACCOUNT_ATS = {"Greenhouse", "Ashby", "Lever"}


def fetch(url=URL, cache=HERE / "data" / "README.md", retries=3):
    """Download once with a descriptive User-Agent and simple backoff; cache to disk."""
    headers = {"User-Agent": "internship-ranker/1.0 (student portfolio project)"}
    for attempt in range(retries):
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            cache.write_text(r.text, encoding="utf-8")
            return r.text
        time.sleep(2 ** attempt)
    r.raise_for_status()


def parse_age(text):
    """'0d' -> 0, '3d' -> 3, '1mo' -> 30, '2mo' -> 60."""
    m = re.match(r"(\d+)\s*(d|mo)", text.strip())
    if not m:
        return None
    n = int(m.group(1))
    return n if m.group(2) == "d" else 30 * n


def ats_of(url):
    u = (url or "").lower()
    return next((name for key, name in ATS_RULES if key in u), "Other")


def clean_url(url):
    return re.sub(r"[?&]utm_source=Simplify&ref=Simplify$", "", url or "")


def parse_readme(text):
    """Return a list of dicts, one per posting row in every category table."""
    rows, last_company = [], None
    # Split on markdown "## " headings so every table knows its category.
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    for section in sections:
        heading, _, body = section.partition("\n")
        if "<table" not in body:
            continue
        category = re.sub(r"^\W+", "", heading).replace(" Internship Roles", "").strip()
        table = BeautifulSoup(body, "lxml")
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 5:
                continue  # header row or malformed
            company_txt = tds[0].get_text(" ", strip=True)
            if company_txt.startswith("↳"):
                company = last_company
            else:
                company = company_txt.replace("🔥", "").strip()
                last_company = company
            title_raw = tds[1].get_text(" ", strip=True)
            flags = [name for sym, name in FLAGS.items() if sym in title_raw]
            title = title_raw
            for sym in FLAGS:
                title = title.replace(sym, "")
            details = tds[2].find("details")
            if details:
                locs = [s.strip() for s in details.get_text("|", strip=True).split("|")[1:] if s.strip()]
            else:
                locs = [s.strip() for s in tds[2].get_text("|", strip=True).split("|") if s.strip()]
            link = tds[3].find("a")
            url = clean_url(link["href"]) if link else ""
            if "🔒" in tds[3].get_text() and "closed" not in flags:
                flags.append("closed")
            ats = ats_of(url)
            rows.append({
                "category": category, "company": company, "title": re.sub(r"\s+", " ", title).strip(),
                "locations": "; ".join(locs), "age_days": parse_age(tds[4].get_text()),
                "flags": ";".join(flags), "ats": ats, "no_account": int(ats in NO_ACCOUNT_ATS),
                "hot": int("🔥" in company_txt), "url": url,
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true", help="parse data/README.md instead of downloading")
    args = ap.parse_args()
    text = (HERE / "data" / "README.md").read_text(encoding="utf-8") if args.cached else fetch()
    rows = parse_readme(text)
    out = HERE / "data" / "postings.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Parsed {len(rows):,} postings across {len({r['category'] for r in rows})} categories -> {out}")


if __name__ == "__main__":
    main()
