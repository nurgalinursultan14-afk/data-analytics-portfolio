# Internship Scraper and Fit Ranker

Hundreds of internships are posted every week, and the good ones close fast (see project 01). This tool scrapes the community-maintained [SimplifyJobs Summer 2027 list](https://github.com/SimplifyJobs/Summer2027-Internships), turns its HTML tables into clean data and ranks every posting for one candidate with a transparent, weighted score. It also checks how much the ranking depends on the chosen weights.

**Tools:** Python (requests, BeautifulSoup, pandas, NumPy, SciPy), pytest.

## How it works

1. **Scrape** (`scraper.py`). One polite request (descriptive User-Agent, retry with backoff, cached to `data/README.md`). The README is split by category heading, and each HTML row is parsed while handling the source's quirks:
   - "↳" rows inherit the company from the row above.
   - Multi-city postings hide their cities inside `<details>` blocks.
   - Eligibility flags in titles (🛂 no sponsorship, 🇺🇸 citizens only, 🔒 closed, 🎓 grad only) become structured fields.
   - Ages ("3d", "1mo") become days, tracking parameters are stripped from URLs, and the applicant-tracking system is identified from the apply link.
2. **Rank** (`ranker.py`). Ineligible postings are dropped, then each posting gets four component scores between 0 and 1:

   | Component | Weight | How it's computed |
   |---|---|---|
   | Role fit | 40% | Best keyword weight in the title ("data analyst" 1.0, "gis" 1.0, "operations" 0.7, ...), multiplied by penalties ("engineer" ×0.5, "phd" ×0, "graduate" ×0.2) |
   | Location | 25% | Best of the posting's cities: NYC 1.0, rest of NY 0.95, remote-US 0.9, nearby states 0.6–0.7, other US 0.35, outside US 0 |
   | Recency | 20% | `0.5 ** (age_days / 7)`: a posting loses half its recency value every week |
   | Apply ease | 15% | 1.0 for no-account systems (Greenhouse, Lever, Ashby), 0.4 otherwise |

   All weights and keywords live in `profile.json`, so the same code ranks for any candidate.
3. **Stress-test the weights.** The ranking is recomputed 200 times with every weight randomly scaled by ±30%. Each run is compared with the base ranking by Kendall's τ and by how much of the top 20 survives.

## Results (Oct 12, 2026 run)

- 1,867 postings scraped across 5 categories. 307 were excluded as graduate-only, and 1,560 were ranked.
- **The ranking is robust to the exact weights:** the mean Kendall's τ is 0.95, and on average 83% of the top 20 stays in the top 20 under perturbation.
- The top matches are NYC analytics roles (for example Dow Jones Data Analyst, Macy's Analytics, Coinbase People Analytics, Schonfeld Business Analytics and Kyndryl Marketing Analysis), followed by strong-fit roles in PA, MA and upstate NY. See `output/top_matches.html` and `output/ranked_postings.csv`.
- Writing the tests caught a real bug: "London, UK" matched the US-state pattern (`, XX`) and scored as a US city. The location parser now checks codes against the list of US states.

## Run it

```bash
pip install requests beautifulsoup4 lxml pandas numpy scipy pytest
python scraper.py          # download and parse -> data/postings.csv   (--cached to reuse data/README.md)
python ranker.py --top 25  # -> output/ranked_postings.csv, output/top_matches.html, output/sensitivity.json
python -m pytest -q        # 5 parser and scoring tests on a hand-built HTML fixture
```

## Limitations

The score ranks fit; it does not decide eligibility. Most postings never state their sponsorship policy (see project 01), so every match still needs a human read before applying. Keyword matching is title-only, and the weights reflect one candidate's priorities.
