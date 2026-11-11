"""Static Python prototype of the Tableau dashboard layout (output/prototype.png).

It shows what each sheet should answer before it is rebuilt interactively in Tableau Public.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent
orders = pd.read_csv(HERE / "data" / "orders.csv", parse_dates=["order_date"])
(HERE / "output").mkdir(exist_ok=True)

BLUE, GREY, RED = "#2a6fdb", "#9aa5b1", "#d64545"
delivered = orders.dropna(subset=["is_late"])
first = orders[orders.is_first_order == 1]

kpis = [
    ("GMV", f"R${orders.gmv.sum() / 1e6:.1f}M"),
    ("Orders", f"{len(orders):,}"),
    ("Late deliveries", f"{delivered.is_late.mean():.1%}"),
    ("Avg review", f"{orders.review_score.mean():.2f} ★"),
    ("Repeat customers", f"{first.customer_returned.mean():.1%}"),
]

fig = plt.figure(figsize=(14, 9))
gs = fig.add_gridspec(3, 5, height_ratios=[0.35, 1, 1], hspace=0.55, wspace=0.6)
fig.suptitle("Olist marketplace: sales, delivery and customer experience (Jan 2017 to Aug 2018)",
             fontsize=14, fontweight="bold", x=0.06, ha="left")

for i, (label, value) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i]); ax.axis("off")
    ax.text(0, 0.65, value, fontsize=20, fontweight="bold", color=BLUE)
    ax.text(0, 0.1, label, fontsize=10, color="#555")

# 1. Monthly GMV
ax = fig.add_subplot(gs[1, :3])
m = orders.groupby("purchase_month").gmv.sum() / 1e6
ax.plot(m.index, m.values, color=BLUE, lw=2)
ax.set_title("Monthly GMV (R$ millions)", loc="left", fontsize=11)
ax.set_xticks(m.index[::3]); ax.tick_params(axis="x", labelsize=8)
ax.spines[["top", "right"]].set_visible(False)

# 2. Review score by lateness
ax = fig.add_subplot(gs[1, 3:])
b = (orders[orders.lateness_bucket != "Not delivered"]
     .groupby("lateness_bucket").review_score.mean())
labels = [s.split(". ", 1)[1] for s in b.index]
ax.barh(labels, b.values, color=[BLUE, BLUE, RED, RED])
ax.invert_yaxis(); ax.set_xlim(0, 5)
ax.set_title("Avg review by delivery vs. promise", loc="left", fontsize=11)
for y, v in enumerate(b.values):
    ax.text(v + 0.05, y, f"{v:.1f}", va="center", fontsize=9)
ax.spines[["top", "right"]].set_visible(False)

# 3. Late rate by state
ax = fig.add_subplot(gs[2, :3])
st = (delivered.groupby("customer_state")
      .agg(late=("is_late", "mean"), n=("is_late", "size")).query("n >= 500")
      .sort_values("late", ascending=False))
ax.bar(st.index, st.late * 100, color=[RED if v > 0.1 else GREY for v in st.late])
ax.set_title("Late-delivery rate by customer state (%, states with 500+ orders)", loc="left", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)

# 4. Top categories by GMV
ax = fig.add_subplot(gs[2, 3:])
c = orders.groupby("main_category").gmv.sum().nlargest(8).sort_values() / 1e6
ax.barh(c.index.str.replace("_", " "), c.values, color=BLUE)
ax.set_title("Top categories by GMV (R$ M)", loc="left", fontsize=11)
ax.tick_params(axis="y", labelsize=8)
ax.spines[["top", "right"]].set_visible(False)

fig.savefig(HERE / "output" / "prototype.png", dpi=110, bbox_inches="tight")
print("saved output/prototype.png")
