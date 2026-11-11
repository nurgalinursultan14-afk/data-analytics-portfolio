"""Build an interactive, self-contained web version of the dashboard (docs/olist-dashboard.html).

It aggregates data/orders.csv into small cubes (month x state x category) and embeds
them in one HTML file that filters in the browser. GitHub Pages serves it from docs/.

Usage:  python build_web_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT = HERE.parent / "docs" / "olist-dashboard.html"
TEMPLATE = HERE / "web_template.html"

orders = pd.read_csv(HERE / "data" / "orders.csv")
top = orders.groupby("main_category").gmv.sum().nlargest(15).index
orders["category"] = orders.main_category.where(orders.main_category.isin(top), "other").str.replace("_", " ")
orders["delivered"] = orders.is_late.notna().astype(int)
orders["reviewed"] = orders.review_score.notna().astype(int)

keys = ["purchase_month", "customer_state", "category"]
cube = orders.groupby(keys).agg(
    o=("order_key", "size"),
    g=("gmv", "sum"),
    d=("delivered", "sum"),
    l=("is_late", "sum"),
    rs=("review_score", "sum"),
    rn=("reviewed", "sum"),
    f=("is_first_order", "sum"),
    fr=("customer_returned", lambda s: int((s * orders.loc[s.index, "is_first_order"]).sum())),
).reset_index()
cube["g"] = cube.g.round(2)

b = orders[orders.lateness_bucket != "Not delivered"]
buckets = b.groupby(keys + ["lateness_bucket"]).agg(rs=("review_score", "sum"), rn=("reviewed", "sum")).reset_index()

dims = {k: sorted(orders[k].unique().tolist()) for k in keys}
bucket_names = sorted(b.lateness_bucket.unique().tolist())
idx = {k: {v: i for i, v in enumerate(vals)} for k, vals in dims.items()}


def encode(df, cols):
    rows = []
    for r in df.itertuples(index=False):
        rec = r._asdict()
        rows.append([idx[k][rec[k]] for k in keys] + [rec[c] if not isinstance(rec[c], float) else round(rec[c], 2) for c in cols])
    return rows


data = {
    "months": dims["purchase_month"],
    "states": dims["customer_state"],
    "categories": dims["category"],
    "buckets": [s.split(". ", 1)[1] for s in bucket_names],
    "cube": encode(cube, ["o", "g", "d", "l", "rs", "rn", "f", "fr"]),
    "bcube": [row[:3] + [bucket_names.index(bk)] + row[3:] for row, bk in
              zip(encode(buckets, ["rs", "rn"]), buckets.lateness_bucket)],
}
html = TEMPLATE.read_text().replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html)
print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB), {len(data['cube'])} cube rows")
