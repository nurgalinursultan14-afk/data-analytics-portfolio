# CLAUDE.md: data-analytics-portfolio

## 1. Project Goal

A public portfolio of end-to-end data analytics projects on real open data, owned by Nursultan (Nurs) Nurgali, a sophomore B.S. Data Analytics student looking for Summer or Winter 2027 internships in data, BI, business or sports analytics. Each project answers one business question, regenerates every number and chart from scripts, and ends in a finding a recruiter can quote. The aim is evidence that gets applications past the automated screen to a human: real SQL, Tableau, dbt, statistics and, next, a sports project.

## 2. Tech Stack & Architecture

- **Language:** Python 3.12 (the version CI uses), with no package manager beyond pip. Dependencies are in `requirements.txt`: pandas, numpy, matplotlib, scipy, statsmodels, scikit-learn, geopandas, libpysal, esda, spreg, mapclassify, requests, beautifulsoup4, lxml, pytest and dbt-duckdb.
- **Databases:** SQLite, built locally by each project's `build_db.py`. DuckDB powers the dbt project (08), which can also run on BigQuery through a second profile target.
- **BI:** Tableau Public (project 07, built from a guide but not yet published). A static HTML/JS dashboard and portfolio site live in `docs/` and are meant to be served by GitHub Pages from `main` `/docs`.
- **Tests and CI:** pytest (project 04 only). `.github/workflows/ci.yml` runs on every push to `main` and every PR: the project 04 tests, `dbt build` with 46 data tests, and the project 09 backtest.
- **Layout:** one numbered folder per project, each self-contained:
  - `README.md` (question, findings, methods, "Run it", limitations)
  - `build_db.py` (downloads raw data and builds the DB), then `run_analysis.py` (runs `sql/NN_*.sql`) for the SQL projects, or `analysis.py` for the Python projects
  - `data/` (raw inputs) and `output/` (CSVs, PNG charts, `results.json`)

| # | Folder | Entry points | On `main`? |
|---|---|---|---|
| 01 | `01-internship-market-sql/` | `extract_history.py`, `build_db.py`, `run_analysis.py` | yes |
| 02 | `02-nyc-heat-vulnerability-gis/` | `analysis.py` | yes |
| 03 | `03-web-analytics-kpi/` | `analysis.py` (writes `output/dashboard.html`) | yes |
| 04 | `04-internship-scraper-ranker/` | `scraper.py`, `ranker.py`, `tests/` | yes |
| 05 | `05-citibike-sql/` | `build_db.py` (~1 GB download), `run_analysis.py` | yes |
| 06 | `06-olist-ecommerce-sql/` | `build_db.py` (~64 MB download), `run_analysis.py` | yes |
| 07 | `07-olist-tableau-dashboard/` | `export_extracts.py`, `prototype.py`, `build_web_dashboard.py` | yes |
| 08 | `08-olist-dbt/` | `dbt build --profiles-dir .` | yes |
| 09 | `09-olist-demand-forecast/` | `forecast.py` | yes |
| — | `docs/` | `index.html`, `olist-dashboard.html` (GitHub Pages) | yes |

Large generated files are git-ignored: `*.db`, `*.duckdb`, the downloaded Citi Bike zip and Olist CSVs, and dbt's `target/` and `logs/`.

## 3. Current Status

**Working (on `main`, PR #3 merged as 994f94d on 2026-11-21)**
- Projects 01–09 are on `main`, each with a README, reproducible scripts and committed outputs.
- Projects 05 (Citi Bike, 4.98M trips) and 06 (Olist, 99k orders) are the SQL showpieces cited on resume v14.
- Project 07 has Tableau-ready extracts, a Python prototype and a web dashboard (`docs/olist-dashboard.html`).
- Project 08 rebuilds project 06 in dbt with 46 data tests. Project 09 backtests 5 forecasting methods.
- CI passed on `main` after the merge (run #4): project 04 tests, `dbt build` and the project 09 backtest.
- The front-page `README.md` has the bio, headline results, CI badge and links to the site and live dashboard.

**Incomplete**
- GitHub Pages: not verified. It must be turned on in Settings → Pages (Deploy from a branch, `main`, `/docs`) before the site and live-dashboard links in the README work.
- Project 07: the Tableau Public version is not published. A TODO in its README asks for the link and a screenshot.
- Contact TODOs: `README.md` has placeholders for the LinkedIn URL, email and resume link, and `docs/index.html` has one for its contact links.
- No sports or football project yet, which is the biggest gap for sports analytics roles.
- No Excel deliverable, so Excel on the resume has nothing to back it.
- Resume v14 lists only 3 projects. Tableau, dbt and forecasting are now on `main` but not on the resume.

**Housekeeping**
- `sql-citibike-project` and `sql-olist-project` are leftover remote branches whose work is already on `main` (PRs #1 and #2). `claude/project-thread-93rkn8` is now merged too (PR #3).
- No `.env` or secrets exist. A future BigQuery target would need a service-account key, which must stay out of git.

## 4. Ordered Next Tasks

1. **Fill the contact TODOs.** Nurs supplies the LinkedIn URL, contact email and resume link. Replace the `<!-- TODO -->` placeholders in `README.md` and `docs/index.html`.
2. **Publish project 07 to Tableau Public.** Nurs builds and publishes it by following `07-olist-tableau-dashboard/README.md`, steps 1–6. Then add the Tableau Public link and a screenshot to the project 07 README and the front page.
3. **Project 10: football scouting in SQL.** Use StatsBomb Open Data (free, with license terms). Load it into SQLite or DuckDB, clean it in SQL, compute per-90 metrics with a minutes threshold, and produce a ranked shortlist for one position. Follow the repo pattern: `build_db.py`, `sql/`, `run_analysis.py`, `output/` and a README with findings and limitations. Add it to the front-page table.
4. **Project 10 dashboard.** Export Tableau extracts for the scouting shortlist the same way project 07 does. Nurs publishes them to Tableau Public, and the link goes into the README.
5. **Excel deliverable.** Make an `.xlsx` with a real PivotTable and XLOOKUP formulas, from the scouting shortlist or the Olist KPIs. Commit it with a short README explaining what each sheet shows.
6. **Housekeeping.** With Nurs's approval, delete the merged remote branches `sql-citibike-project`, `sql-olist-project` and `claude/project-thread-93rkn8`, and extend CI to cover any new tests.

## 5. Operational Rules & Guardrails

- **One task at a time.** Execute only ONE numbered task from section 4, then stop, report what changed and how it was verified, and wait for Nurs's confirmation before starting the next.
- **Stay in this repo.** Never read or modify files outside this repository's root folder.
- **No secrets.** Never commit `.env` files, API keys, BigQuery service-account JSON, `profiles.yml` entries containing credentials, or personal contact details that Nurs hasn't approved for the public README.
- **Branches.** Never push directly to `main` or `master`. Work on a feature branch and open a PR only when Nurs asks. Nurs approves every merge and every branch deletion.
- **Keep data out of git.** Don't commit raw downloads or built databases (`*.db`, `*.duckdb`, zips, large CSVs). Update `.gitignore` when a new project adds any.
- **Reproducible numbers only.** Every figure in a README must come from a committed script's output. Don't hand-type or round numbers that the scripts don't produce.
- **Verify before claiming.** Before any commit, run `python -m py_compile` on the changed `.py` files, `python -m pytest -q 04-internship-scraper-ranker/tests` if project 04 changed, and `dbt build --profiles-dir .` in `08-olist-dbt/` if project 08 changed.
- **Things Claude can't do.** Claude never signs in to, publishes on or submits to external accounts (Tableau Public, LinkedIn, job portals). It prepares the work, and Nurs publishes it.
- **Keep this file current.** After finishing any task, update section 3 (Current Status) and section 4 (Ordered Next Tasks) in this file, in the same commit as the work.
