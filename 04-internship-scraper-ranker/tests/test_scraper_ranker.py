"""Unit tests: python -m pytest -q"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ranker import build_features, location_score, role_fit, score  # noqa: E402
from scraper import parse_age, parse_readme  # noqa: E402

FIXTURE = """
## 🤖 Data Science, AI & Machine Learning Internship Roles
<table><thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th></tr></thead>
<tbody>
<tr><td>🔥 <strong><a href="https://simplify.jobs/c/Acme">Acme</a></strong></td><td>Data Analyst Intern</td>
<td>NYC</td><td><div align="center"><a href="https://job-boards.greenhouse.io/acme/jobs/1?utm_source=Simplify&ref=Simplify">Apply</a></div></td><td>2d</td></tr>
<tr><td>↳</td><td>Research Intern 🎓</td>
<td><details><summary><strong>2 locations</strong></summary>Austin, TX<br>Remote in USA</details></td>
<td><div align="center"><a href="https://acme.wd1.myworkdayjobs.com/x">Apply</a></div></td><td>1mo</td></tr>
<tr><td><strong>Beta</strong></td><td>Ops Analyst Intern 🛂</td><td>Boston, MA</td><td>🔒</td><td>5d</td></tr>
</tbody></table>
"""
PROFILE = json.loads((ROOT / "profile.json").read_text())


def test_parse_rows_and_continuation():
    rows = parse_readme(FIXTURE)
    assert len(rows) == 3
    assert rows[1]["company"] == "Acme"                     # "↳" inherits the company above
    assert rows[0]["hot"] == 1 and rows[0]["company"] == "Acme"
    assert rows[0]["category"] == "Data Science, AI & Machine Learning"


def test_flags_locations_ats():
    rows = parse_readme(FIXTURE)
    assert rows[0]["ats"] == "Greenhouse" and rows[0]["no_account"] == 1
    assert "utm_source" not in rows[0]["url"]
    assert rows[1]["locations"] == "Austin, TX; Remote in USA"
    assert rows[1]["flags"] == "grad_only" and rows[1]["title"] == "Research Intern"
    assert set(rows[2]["flags"].split(";")) == {"no_sponsorship", "closed"}


def test_parse_age():
    assert parse_age("0d") == 0 and parse_age("12d") == 12 and parse_age("1mo") == 30
    assert parse_age("n/a") is None


def test_role_and_location_scores():
    kw, pen = PROFILE["role_keywords"], PROFILE["role_penalties"]
    assert role_fit("Data Analyst Intern", kw, pen) == 1.0
    assert role_fit("Software Engineer Intern", kw, pen) == 0.0
    assert role_fit("Data Engineer Intern", kw, pen) < role_fit("Data Analyst Intern", kw, pen)
    assert location_score("NYC", PROFILE) == 1.0
    assert location_score("Austin, TX; Remote in USA", PROFILE) == PROFILE["location_scores"]["Remote"]
    assert location_score("London, UK", PROFILE) == 0.0


def test_exclusions_and_ordering():
    df = pd.DataFrame(parse_readme(FIXTURE))
    feats, dropped = build_features(df, PROFILE)
    assert dropped == 2 and list(feats.title) == ["Data Analyst Intern"]
    s = score(feats, PROFILE)
    assert 0 <= s.iloc[0] <= 100
