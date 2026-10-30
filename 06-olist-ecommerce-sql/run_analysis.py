"""Run every query in sql/, save results as CSV, and draw the charts used in the README.

Usage:  python build_db.py && python run_analysis.py
"""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "output"
con = sqlite3.connect(OUT / "olist.db")

results = {}
for f in sorted((HERE / "sql").glob("[0-9][0-9]_*.sql")):
    if f.name.startswith("00_"):
        continue
    df = pd.read_sql_query(f.read_text(), con)
    df.to_csv(OUT / f"{f.stem}.csv", index=False)
    results[f.stem] = df
    print(f"\n=== {f.stem} ===\n{df.to_string(index=False, max_rows=40)}")

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10})

# Chart 1: monthly GMV with 3-month average
m = results["02_monthly_kpis"]
fig, ax = plt.subplots(figsize=(10, 3.8))
ax.bar(m.purchase_month, m.gmv_brl / 1e6, color="#A9C3E0", label="Monthly GMV")
ax.plot(m.purchase_month, m.gmv_3mo_avg / 1e6, color="#2F5D8C", lw=2, label="3-month average")
ax.set_ylabel("GMV (million BRL)")
ax.set_title("Monthly GMV grew about 8x from Jan 2017 to early 2018, then flattened (spike = Black Friday)")
ax.tick_params(axis="x", rotation=90, labelsize=8)
ax.legend(frameon=False, loc="upper left")
plt.tight_layout()
plt.savefig(OUT / "chart_monthly_gmv.png")
plt.close()

# Chart 2: review stars by delivery lateness
d = results["05_late_delivery_reviews"]
labels = d.delivery.str[3:]
fig, ax = plt.subplots(figsize=(7.5, 3.8))
ax.bar(labels, d.pct_1_star, color="#C44E52", label="1-star reviews")
ax.bar(labels, d.pct_5_star, bottom=d.pct_1_star, color="#55A868", label="5-star reviews")
for i, v in enumerate(d.avg_stars):
    ax.text(i, d.pct_1_star[i] + d.pct_5_star[i] + 2, f"avg {v:.1f}★", ha="center", fontsize=9)
ax.set_ylim(0, 100)
ax.set_ylabel("% of reviews")
ax.set_title("Late deliveries turn 5-star reviews into 1-star reviews")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
plt.tight_layout()
plt.savefig(OUT / "chart_late_reviews.png")
plt.close()

# Chart 3: seller Pareto curve (every seller, same revenue definition as 08)
p = pd.read_sql_query("""
    SELECT SUM(i.price) AS revenue
    FROM order_items i JOIN sales s ON s.order_id = i.order_id
    GROUP BY i.seller_id ORDER BY revenue DESC
""", con)
p["cum_sellers"] = 100 * (p.index + 1) / len(p)
p["cum_revenue"] = 100 * p.revenue.cumsum() / p.revenue.sum()
fig, ax = plt.subplots(figsize=(5.5, 4))
ax.plot(p.cum_sellers, p.cum_revenue, color="#8172B3", lw=2)
ax.plot([0, 100], [0, 100], color="#BBBBBB", ls="--", lw=1)
top20 = results["08_seller_concentration"].set_index("top_sellers_pct").loc[20, "pct_of_revenue"]
ax.axvline(20, color="#999999", lw=0.8)
ax.annotate(f"top 20% of sellers\n= {top20:.0f}% of revenue", (20, top20), (32, 55),
            arrowprops=dict(arrowstyle="->", color="#555555"), fontsize=9)
ax.set_xlabel("% of sellers (largest first)")
ax.set_ylabel("% of revenue")
ax.set_title("Seller revenue concentration")
plt.tight_layout()
plt.savefig(OUT / "chart_seller_pareto.png")
plt.close()

# Chart 4: RFM segments, share of customers vs. share of revenue
r = results["09_rfm_segments"].iloc[::-1]
fig, ax = plt.subplots(figsize=(7.5, 3.8))
y = range(len(r))
ax.barh([i + 0.2 for i in y], r.pct_customers, height=0.4, color="#4C72B0", label="% of customers")
ax.barh([i - 0.2 for i in y], r.pct_revenue, height=0.4, color="#DD8452", label="% of revenue")
ax.set_yticks(list(y), r.segment.str[3:])
ax.set_xlabel("%")
ax.set_title("RFM segments: one-time buyers bring 96% of revenue")
ax.legend(frameon=False, loc="upper right")
plt.tight_layout()
plt.savefig(OUT / "chart_rfm_segments.png")
plt.close()

print("\nCharts saved to", OUT)
