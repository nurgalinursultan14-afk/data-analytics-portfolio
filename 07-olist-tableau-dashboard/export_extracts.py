"""Export tidy, Tableau-ready extracts from the Olist SQLite database built in project 06.

Usage:
    python ../06-olist-ecommerce-sql/build_db.py   # once, builds ../06-olist-ecommerce-sql/output/olist.db
    python export_extracts.py                      # -> data/*.csv
"""
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DB = HERE.parent / "06-olist-ecommerce-sql" / "output" / "olist.db"
OUT = HERE / "data"

# One row per order in the analysis window (complete months Jan 2017 to Aug 2018, no cancellations).
# Hashed ids are swapped for short integers so the file stays small enough for Tableau Public.
ORDERS_SQL = """
WITH first_order AS (
    SELECT customer_unique_id, MIN(purchased_at) AS first_purchase
    FROM sales GROUP BY customer_unique_id
),
repeaters AS (   -- bought again on a later day (same-day split checkouts don't count, as in project 06)
    SELECT s.customer_unique_id
    FROM sales s JOIN first_order f USING (customer_unique_id)
    WHERE date(s.purchased_at) > date(f.first_purchase)
    GROUP BY s.customer_unique_id
),
main_category AS (   -- category of the most expensive item in the order
    SELECT order_id, category FROM (
        SELECT oi.order_id, p.category,
               ROW_NUMBER() OVER (PARTITION BY oi.order_id ORDER BY oi.price DESC, oi.order_item_id) AS rn
        FROM order_items oi JOIN products p USING (product_id)
    ) WHERE rn = 1
)
SELECT DENSE_RANK() OVER (ORDER BY s.order_id)             AS order_key,
       DENSE_RANK() OVER (ORDER BY s.customer_unique_id)   AS customer_key,
       date(s.purchased_at)                                AS order_date,
       s.purchase_month,
       s.customer_state,
       mc.category                                         AS main_category,
       s.n_items,
       s.gmv,
       ROUND(s.freight_value, 2)                           AS freight_value,
       s.days_to_deliver,
       CAST(julianday(date(s.delivered_at)) - julianday(date(s.estimated_delivery)) AS INTEGER)
                                                           AS days_vs_promise,
       s.is_late,
       s.review_score,
       CASE WHEN s.purchased_at = f.first_purchase THEN 1 ELSE 0 END AS is_first_order,
       CASE WHEN r.customer_unique_id IS NULL THEN 0 ELSE 1 END     AS customer_returned
FROM sales s
JOIN first_order f USING (customer_unique_id)
LEFT JOIN repeaters r USING (customer_unique_id)
LEFT JOIN main_category mc ON mc.order_id = s.order_id
"""

# One row per seller: for the Pareto / seller-concentration view.
SELLERS_SQL = """
SELECT DENSE_RANK() OVER (ORDER BY oi.seller_id) AS seller_key,
       se.state                                  AS seller_state,
       COUNT(DISTINCT oi.order_id)               AS orders,
       ROUND(SUM(oi.price), 2)                   AS item_revenue,
       ROUND(AVG(s.review_score), 2)             AS avg_review,
       ROUND(AVG(s.is_late), 4)                  AS late_rate
FROM order_items oi
JOIN sales s ON s.order_id = oi.order_id
JOIN sellers se ON se.seller_id = oi.seller_id
GROUP BY oi.seller_id
"""


def lateness_bucket(d):
    if pd.isna(d):
        return "Not delivered"
    if d <= -7:
        return "1. 7+ days early"
    if d <= 0:
        return "2. 0-6 days early"
    if d <= 7:
        return "3. 1-7 days late"
    return "4. 8+ days late"


def main():
    if not DB.exists():
        raise SystemExit(f"{DB} not found. Run ../06-olist-ecommerce-sql/build_db.py first.")
    OUT.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    orders = pd.read_sql(ORDERS_SQL, con)
    orders["lateness_bucket"] = orders["days_vs_promise"].map(lateness_bucket)
    for col in ["days_vs_promise", "is_late", "review_score"]:
        orders[col] = orders[col].astype("Int64")   # whole numbers, blank when missing
    sellers = pd.read_sql(SELLERS_SQL, con)
    orders.to_csv(OUT / "orders.csv", index=False)
    sellers.to_csv(OUT / "sellers.csv", index=False)

    # Sanity checks against project 06's published numbers
    first = orders[orders.is_first_order == 1]
    print(f"orders.csv: {len(orders):,} rows, {orders.customer_key.nunique():,} customers")
    print(f"repeat rate: {first.customer_returned.mean():.1%}")
    print(f"late rate (delivered): {orders.is_late.mean():.1%}")
    print(f"sellers.csv: {len(sellers):,} rows")


if __name__ == "__main__":
    main()
