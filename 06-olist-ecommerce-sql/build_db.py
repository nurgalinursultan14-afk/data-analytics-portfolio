"""Build a normalized SQLite database from the public Olist Brazilian e-commerce dataset.

Usage:  python build_db.py            -> downloads the CSVs if needed, creates output/olist.db
"""
import csv
import sqlite3
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
DB = HERE / "output" / "olist.db"
BASE_URL = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"

# raw table name -> source file (the geolocation file is not needed: states come from customers/sellers)
FILES = {
    "raw_orders": "olist_orders_dataset.csv",
    "raw_customers": "olist_customers_dataset.csv",
    "raw_order_items": "olist_order_items_dataset.csv",
    "raw_payments": "olist_order_payments_dataset.csv",
    "raw_reviews": "olist_order_reviews_dataset.csv",
    "raw_products": "olist_products_dataset.csv",
    "raw_sellers": "olist_sellers_dataset.csv",
    "raw_category_names": "product_category_name_translation.csv",
}


def download():
    DATA.mkdir(exist_ok=True)
    for name in FILES.values():
        path = DATA / name
        if not path.exists():
            print(f"Downloading {name} ...")
            urllib.request.urlretrieve(BASE_URL + name, path)


def load_raw(con):
    """Stage every CSV as an all-text table; 00_schema.sql does the typing and cleaning in SQL."""
    for table, name in FILES.items():
        with open(DATA / name, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            cols = next(reader)
            con.execute(f"CREATE TABLE {table} ({', '.join(c + ' TEXT' for c in cols)})")
            con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(cols))})", reader)


def main():
    download()
    DB.parent.mkdir(exist_ok=True)
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    load_raw(con)
    con.executescript((HERE / "sql" / "00_schema.sql").read_text())
    con.commit()
    con.execute("VACUUM")
    for t in ("customers", "orders", "order_items", "payments", "reviews", "products", "sellers"):
        print(f"{t}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:,} rows")
    con.close()


if __name__ == "__main__":
    main()
