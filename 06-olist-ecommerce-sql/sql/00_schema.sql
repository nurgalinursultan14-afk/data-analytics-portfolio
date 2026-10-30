-- Relational model of the Olist marketplace. build_db.py stages each CSV as an all-text raw_*
-- table; this file types, cleans and loads them into the tables below with plain SQL.

CREATE TABLE customers (
    customer_id         TEXT PRIMARY KEY,   -- one per ORDER (Olist issues a new id every purchase)
    customer_unique_id  TEXT NOT NULL,      -- the actual person; use this for retention
    zip_prefix          TEXT,
    city                TEXT,
    state               TEXT
);
INSERT INTO customers
SELECT customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state
FROM raw_customers;
CREATE INDEX ix_customers_unique ON customers(customer_unique_id);

CREATE TABLE sellers (
    seller_id   TEXT PRIMARY KEY,
    zip_prefix  TEXT,
    city        TEXT,
    state       TEXT
);
INSERT INTO sellers SELECT seller_id, seller_zip_code_prefix, seller_city, seller_state FROM raw_sellers;

-- Category names are Portuguese in the source; translate them and label missing ones.
CREATE TABLE products (
    product_id   TEXT PRIMARY KEY,
    category     TEXT NOT NULL,
    weight_g     REAL,
    photos_qty   INTEGER
);
INSERT INTO products
SELECT p.product_id,
       COALESCE(t.product_category_name_english, NULLIF(p.product_category_name, ''), 'unknown'),
       CAST(NULLIF(p.product_weight_g, '') AS REAL),
       CAST(NULLIF(p.product_photos_qty, '') AS INTEGER)
FROM raw_products p
LEFT JOIN raw_category_names t ON t.product_category_name = p.product_category_name;

CREATE TABLE orders (
    order_id            TEXT PRIMARY KEY,
    customer_id         TEXT NOT NULL REFERENCES customers(customer_id),
    status              TEXT NOT NULL,
    purchased_at        TEXT NOT NULL,
    approved_at         TEXT,
    shipped_at          TEXT,      -- handed to the carrier
    delivered_at        TEXT,      -- reached the customer
    estimated_delivery  TEXT       -- date promised to the customer at checkout
);
INSERT INTO orders
SELECT order_id, customer_id, order_status, order_purchase_timestamp,
       NULLIF(order_approved_at, ''), NULLIF(order_delivered_carrier_date, ''),
       NULLIF(order_delivered_customer_date, ''), NULLIF(order_estimated_delivery_date, '')
FROM raw_orders;
CREATE INDEX ix_orders_customer ON orders(customer_id);

CREATE TABLE order_items (
    order_id       TEXT NOT NULL REFERENCES orders(order_id),
    order_item_id  INTEGER NOT NULL,          -- 1, 2, 3 ... within the order
    product_id     TEXT NOT NULL REFERENCES products(product_id),
    seller_id      TEXT NOT NULL REFERENCES sellers(seller_id),
    price          REAL NOT NULL,             -- BRL
    freight        REAL NOT NULL,             -- BRL
    PRIMARY KEY (order_id, order_item_id)
);
INSERT INTO order_items
SELECT order_id, CAST(order_item_id AS INTEGER), product_id, seller_id,
       CAST(price AS REAL), CAST(freight_value AS REAL)
FROM raw_order_items;
CREATE INDEX ix_items_seller ON order_items(seller_id);

CREATE TABLE payments (
    order_id      TEXT NOT NULL REFERENCES orders(order_id),
    sequence      INTEGER NOT NULL,
    type          TEXT NOT NULL,              -- credit_card, boleto (bank slip), voucher, debit_card
    installments  INTEGER,
    value         REAL NOT NULL,
    PRIMARY KEY (order_id, sequence)
);
INSERT INTO payments
SELECT order_id, CAST(payment_sequential AS INTEGER), payment_type,
       CAST(payment_installments AS INTEGER), CAST(payment_value AS REAL)
FROM raw_payments;

-- About 550 orders have more than one review. Keep the most recently answered one per order.
CREATE TABLE reviews (
    order_id     TEXT PRIMARY KEY REFERENCES orders(order_id),
    review_id    TEXT NOT NULL,
    score        INTEGER NOT NULL,            -- 1 to 5 stars
    has_comment  INTEGER NOT NULL,
    created_at   TEXT
);
INSERT INTO reviews
SELECT order_id, review_id, score, has_comment, created_at
FROM (
    SELECT order_id, review_id, CAST(review_score AS INTEGER) AS score,
           (review_comment_message <> '') AS has_comment,
           review_creation_date AS created_at,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY review_answer_timestamp DESC, review_id) AS rn
    FROM raw_reviews
)
WHERE rn = 1;

-- One row per order with everything most questions need. Revenue is the item price plus
-- freight from order_items (gross merchandise value), not the payments table, because a few
-- hundred orders were paid partly with vouchers that do not match the item total.
CREATE VIEW order_facts AS
WITH items AS (
    SELECT order_id, COUNT(*) AS n_items, SUM(price) AS item_value, SUM(freight) AS freight_value
    FROM order_items GROUP BY order_id
)
SELECT o.order_id,
       c.customer_unique_id,
       c.state                                            AS customer_state,
       o.status,
       o.purchased_at,
       substr(o.purchased_at, 1, 7)                       AS purchase_month,
       i.n_items,
       ROUND(i.item_value + i.freight_value, 2)           AS gmv,
       i.freight_value,
       o.delivered_at,
       o.estimated_delivery,
       ROUND(julianday(o.delivered_at) - julianday(o.purchased_at), 1)   AS days_to_deliver,
       CASE WHEN o.delivered_at IS NULL THEN NULL
            WHEN date(o.delivered_at) > date(o.estimated_delivery) THEN 1 ELSE 0 END AS is_late,
       r.score                                            AS review_score
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN items i ON i.order_id = o.order_id
LEFT JOIN reviews r ON r.order_id = o.order_id;

-- Analysis window: complete months only (Jan 2017 to Aug 2018). Sep to Dec 2016 has a few
-- hundred test-like orders and Sep/Oct 2018 has only 20.
CREATE VIEW sales AS
SELECT * FROM order_facts
WHERE status NOT IN ('canceled', 'unavailable')
  AND gmv IS NOT NULL
  AND purchase_month BETWEEN '2017-01' AND '2018-08';

DROP TABLE raw_orders;
DROP TABLE raw_customers;
DROP TABLE raw_order_items;
DROP TABLE raw_payments;
DROP TABLE raw_reviews;
DROP TABLE raw_products;
DROP TABLE raw_sellers;
DROP TABLE raw_category_names;
