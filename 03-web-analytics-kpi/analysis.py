"""E-commerce web analytics: KPIs, segment tests, conversion drivers, and experiment sizing.

Data: UCI "Online Shoppers Purchasing Intention" (12,330 Google Analytics sessions from one
online store over one year; Sakar et al., 2018, CC BY 4.0).

Usage:  python analysis.py      -> charts, tables, results.json and dashboard.html in output/
"""
import base64
import json
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_confint, proportions_ztest, proportion_effectsize

HERE = Path(__file__).parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
BLUE, ORANGE, GRAY = "#4C72B0", "#DD8452", "#999999"

df = pd.read_csv(HERE / "data" / "online_shoppers_intention.csv")
df["converted"] = df["Revenue"].astype(int)
df["pages"] = df[["Administrative", "Informational", "ProductRelated"]].sum(axis=1)
df["duration_min"] = df[["Administrative_Duration", "Informational_Duration",
                         "ProductRelated_Duration"]].sum(axis=1) / 60
df["Month"] = df["Month"].replace({"June": "Jun"})
MONTHS = ["Feb", "Mar", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]  # no Jan/Apr in data
R = {}

# ------------------------------------------------------------------ 1. headline KPIs
def rate_ci(k, n):
    lo, hi = proportion_confint(k, n, method="wilson")
    return k / n, lo, hi

cr, lo, hi = rate_ci(df.converted.sum(), len(df))
R["kpis"] = {
    "sessions": len(df),
    "conversion_rate": round(cr, 4), "conversion_ci95": [round(lo, 4), round(hi, 4)],
    "single_page_sessions_pct": round((df.pages <= 1).mean(), 4),
    "avg_bounce_rate": round(df.BounceRates.mean(), 4),
    "avg_exit_rate": round(df.ExitRates.mean(), 4),
    "median_pages_per_session": float(df.pages.median()),
    "median_session_minutes": round(df.duration_min.median(), 1),
    "returning_visitor_share": round((df.VisitorType == "Returning_Visitor").mean(), 4),
}

# ------------------------------------------------------------------ 2. KPIs by segment, with CIs
def seg_table(col, order=None):
    g = df.groupby(col).agg(sessions=("converted", "size"), conversions=("converted", "sum"),
                            bounce=("BounceRates", "mean"), pages=("pages", "median"))
    ci = g.apply(lambda r: pd.Series(rate_ci(r.conversions, r.sessions),
                                     index=["conv_rate", "ci_lo", "ci_hi"]), axis=1)
    g = g.join(ci)
    if order:
        g = g.reindex([o for o in order if o in g.index])
    return g

month = seg_table("Month", MONTHS)
visitor = seg_table("VisitorType", ["New_Visitor", "Returning_Visitor", "Other"])
weekend = seg_table("Weekend")
top_traffic = df.TrafficType.value_counts().head(8).index
traffic = seg_table("TrafficType").loc[top_traffic].sort_values("conv_rate")
for name, t in [("month", month), ("visitor", visitor), ("weekend", weekend), ("traffic", traffic)]:
    t.round(4).to_csv(OUT / f"kpi_by_{name}.csv")

R["month_conv_rate"] = month.conv_rate.round(4).to_dict()
R["best_month"] = month.conv_rate.idxmax()
R["nov_share_of_conversions"] = round(month.loc["Nov", "conversions"] / df.converted.sum(), 3)

# Observational comparison of new vs. returning visitors (a z-test, NOT an experiment)
nv, rv = visitor.loc["New_Visitor"], visitor.loc["Returning_Visitor"]
z, p = proportions_ztest([nv.conversions, rv.conversions], [nv.sessions, rv.sessions])
R["new_vs_returning"] = {"new_rate": round(nv.conv_rate, 4), "returning_rate": round(rv.conv_rate, 4),
                         "z": round(z, 2), "p": float(p)}
we, wd = weekend.loc[True], weekend.loc[False]
z2, p2 = proportions_ztest([we.conversions, wd.conversions], [we.sessions, wd.sessions])
R["weekend_vs_weekday"] = {"weekend_rate": round(we.conv_rate, 4), "weekday_rate": round(wd.conv_rate, 4),
                           "z": round(z2, 2), "p": float(p2)}
chi2, p_tr, dof, _ = stats.chi2_contingency(pd.crosstab(df[df.TrafficType.isin(top_traffic)].TrafficType,
                                                         df.converted))
R["traffic_type_chi2"] = {"chi2": round(chi2, 1), "dof": int(dof), "p": float(p_tr)}

# ------------------------------------------------------------------ 3. engagement funnel
bins = [-1, 0, 5, 15, 30, 60, 10_000]
labels = ["0", "1-5", "6-15", "16-30", "31-60", "60+"]
df["product_pages_bucket"] = pd.cut(df.ProductRelated, bins=bins, labels=labels)
funnel = df.groupby("product_pages_bucket", observed=True).agg(
    sessions=("converted", "size"), conv_rate=("converted", "mean"))
funnel.round(4).to_csv(OUT / "conversion_by_product_pages.csv")
R["conv_by_product_pages"] = funnel.conv_rate.round(4).to_dict()
R["conv_rate_with_page_value"] = round(df[df.PageValues > 0].converted.mean(), 4)
R["conv_rate_without_page_value"] = round(df[df.PageValues == 0].converted.mean(), 4)
R["share_sessions_with_page_value"] = round((df.PageValues > 0).mean(), 4)

# ------------------------------------------------------------------ 4. what predicts conversion?
num = ["Administrative", "Administrative_Duration", "Informational", "Informational_Duration",
       "ProductRelated", "ProductRelated_Duration", "BounceRates", "ExitRates", "SpecialDay"]
cat = ["Month", "VisitorType", "Weekend", "TrafficType"]
cv = StratifiedKFold(5, shuffle=True, random_state=0)

def model(features_num):
    pre = ColumnTransformer([("num", StandardScaler(), features_num),
                             ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=50), cat)])
    return make_pipeline(pre, LogisticRegression(max_iter=2000, class_weight="balanced"))

auc_with = cross_val_score(model(num + ["PageValues"]), df, df.converted, cv=cv, scoring="roc_auc")
auc_without = cross_val_score(model(num), df, df.converted, cv=cv, scoring="roc_auc")
R["logit_auc_with_pagevalues"] = [round(auc_with.mean(), 3), round(auc_with.std(), 3)]
R["logit_auc_without_pagevalues"] = [round(auc_without.mean(), 3), round(auc_without.std(), 3)]

# Interpretable model (statsmodels) without PageValues, with explicit reference categories:
# numeric features standardized (odds ratio per +1 SD); May / Returning visitor / Traffic type 2 as baselines.
import statsmodels.formula.api as smf
d = df.copy()
for c in num:
    d[c + "_z"] = (d[c] - d[c].mean()) / d[c].std()
d["Traffic"] = np.where(d.TrafficType.isin(top_traffic), d.TrafficType.astype(str), "other")
d["Weekend"] = d["Weekend"].astype(int)
formula = ("converted ~ " + " + ".join(c + "_z" for c in num) +
           " + C(Month, Treatment('May')) + C(VisitorType, Treatment('Returning_Visitor'))"
           " + Weekend + C(Traffic, Treatment('2'))")
logit = smf.logit(formula, data=d).fit(disp=0)
(OUT / "logit_summary.txt").write_text(str(logit.summary()))
ors = pd.DataFrame({"odds_ratio": np.exp(logit.params), "p_value": logit.pvalues}).drop("Intercept")
ors.index = (ors.index.str.replace("_z", " (+1 SD)").str.replace(r"C\((\w+).*?\)\[T\.(.+)\]", r"\1 = \2", regex=True))
sig = ors[ors.p_value < 0.05]
top = np.log(sig.odds_ratio).reindex(np.log(sig.odds_ratio).abs().sort_values(ascending=False).index).head(10)
ors.round(4).sort_values("p_value").to_csv(OUT / "conversion_drivers_odds_ratios.csv")
R["top_drivers_odds_ratio"] = np.exp(top).round(2).to_dict()
R["logit_pseudo_r2"] = round(logit.prsquared, 3)

# ------------------------------------------------------------------ 5. experiment sizing
# How many sessions per arm would a checkout-page A/B test need to detect a lift from the
# observed baseline? (alpha = 0.05 two-sided, power = 0.8)
power = NormalIndPower()
sizing = []
for rel_lift in [0.05, 0.10, 0.15, 0.20]:
    es = proportion_effectsize(cr * (1 + rel_lift), cr)
    n = power.solve_power(effect_size=es, alpha=0.05, power=0.8, ratio=1)
    sizing.append({"relative_lift": f"{int(rel_lift*100)}%", "target_rate": round(cr * (1 + rel_lift), 4),
                   "sessions_per_arm": int(np.ceil(n))})
pd.DataFrame(sizing).to_csv(OUT / "ab_test_sample_sizes.csv", index=False)
R["ab_test_sizing"] = sizing

# ------------------------------------------------------------------ 6. charts
charts = {}

def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png")
    buf = BytesIO()
    fig.savefig(buf, format="png")
    charts[name] = base64.b64encode(buf.getvalue()).decode()
    plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 3.4))
x = range(len(month))
ax.bar(x, month.conv_rate * 100, color=[ORANGE if mth == "Nov" else BLUE for mth in month.index])
ax.errorbar(x, month.conv_rate * 100, yerr=[(month.conv_rate - month.ci_lo) * 100,
            (month.ci_hi - month.conv_rate) * 100], fmt="none", ecolor="#333", capsize=3, lw=.8)
ax.set_xticks(list(x), month.index)
ax.set_ylabel("Conversion rate (%)")
ax.set_title("Conversion rate by month (95% CI)")
save(fig, "chart_conversion_by_month")

fig, ax = plt.subplots(figsize=(7, 3.4))
ax.bar(funnel.index.astype(str), funnel.conv_rate * 100, color=BLUE)
for i, (r, n) in enumerate(zip(funnel.conv_rate, funnel.sessions)):
    ax.annotate(f"{r*100:.0f}%\n(n={n:,})", (i, r * 100), ha="center", va="bottom", fontsize=7.5)
ax.set_xlabel("Product pages viewed in session")
ax.set_ylabel("Conversion rate (%)")
ax.set_ylim(0, funnel.conv_rate.max() * 130)
ax.set_title("Deeper product browsing goes with higher conversion")
save(fig, "chart_conversion_by_depth")

fig, ax = plt.subplots(figsize=(7, 3.4))
tl = [f"Type {t}" for t in traffic.index]
ax.barh(tl, traffic.conv_rate * 100, xerr=[(traffic.conv_rate - traffic.ci_lo) * 100,
        (traffic.ci_hi - traffic.conv_rate) * 100], color=BLUE, ecolor="#333", capsize=3)
ax.axvline(cr * 100, color=GRAY, ls="--", lw=1)
ax.text(cr * 100, len(tl) - .4, f" site avg {cr*100:.1f}%", color=GRAY, fontsize=8)
ax.set_xlabel("Conversion rate (%)")
ax.set_title("Conversion rate by traffic source (8 largest, 95% CI)")
save(fig, "chart_conversion_by_traffic")

fig, ax = plt.subplots(figsize=(7, 3.6))
t = top.iloc[::-1]
ax.barh(t.index, np.exp(t), color=[ORANGE if v > 0 else BLUE for v in t])
ax.axvline(1, color="#333", lw=.8)
ax.set_xscale("log")
ax.set_xlabel("Odds ratio (log scale; >1 raises conversion odds)")
ax.set_title("Strongest significant conversion drivers (logit, p<0.05, PageValues excluded)", fontsize=8.5)
save(fig, "chart_drivers")

# ------------------------------------------------------------------ 7. one-file KPI dashboard
k = R["kpis"]
tiles = [("Sessions", f"{k['sessions']:,}"), ("Conversion rate", f"{k['conversion_rate']*100:.1f}%"),
         ("Avg bounce rate", f"{k['avg_bounce_rate']*100:.1f}%"),
         ("Median pages / session", f"{k['median_pages_per_session']:.0f}"),
         ("Median session length", f"{k['median_session_minutes']} min"),
         ("Returning visitors", f"{k['returning_visitor_share']*100:.0f}%")]
tile_html = "".join(f'<div class="tile"><div class="v">{v}</div><div class="l">{l}</div></div>'
                    for l, v in tiles)
img_html = "".join(f'<img alt="{n}" src="data:image/png;base64,{b}">' for n, b in charts.items())
size_rows = "".join(f"<tr><td>{s['relative_lift']}</td><td>{s['target_rate']*100:.1f}%</td>"
                    f"<td>{s['sessions_per_arm']:,}</td></tr>" for s in sizing)
html = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>E-commerce KPI Dashboard</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:24px auto;max-width:1100px;padding:0 16px;color:#222}}
h1{{font-size:22px;margin-bottom:4px}} .sub{{color:#666;margin-top:0}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}}
.tile{{border:1px solid #e3e3e3;border-radius:10px;padding:14px}} .v{{font-size:24px;font-weight:600}} .l{{color:#666;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px}} img{{width:100%;border:1px solid #eee;border-radius:8px}}
table{{border-collapse:collapse;margin-top:8px}} td,th{{border-bottom:1px solid #eee;padding:6px 12px;text-align:left}}
</style></head><body>
<h1>E-commerce KPI Dashboard</h1>
<p class="sub">12,330 Google Analytics sessions from one online store (UCI Online Shoppers Purchasing Intention dataset).</p>
<div class="tiles">{tile_html}</div><div class="grid">{img_html}</div>
<h3>Sample size for a future A/B test (α = 0.05, power = 0.8)</h3>
<table><tr><th>Relative lift to detect</th><th>Target conversion</th><th>Sessions per arm</th></tr>{size_rows}</table>
</body></html>"""
(OUT / "dashboard.html").write_text(html)

(OUT / "results.json").write_text(json.dumps(R, indent=2, default=str))
print(json.dumps(R, indent=2, default=str))
