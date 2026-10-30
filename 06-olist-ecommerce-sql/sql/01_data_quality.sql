-- Q1. What is in the raw data, and what does the analysis keep?
SELECT 'Orders in the source'                                   AS check_name, COUNT(*) AS n FROM orders
UNION ALL
SELECT 'Customer IDs (one per order)',                          COUNT(*) FROM customers
UNION ALL
SELECT 'Distinct people (customer_unique_id)',                  COUNT(DISTINCT customer_unique_id) FROM customers
UNION ALL
SELECT 'Canceled or unavailable orders',                        SUM(status IN ('canceled', 'unavailable')) FROM orders
UNION ALL
SELECT 'Orders with no items',                                  COUNT(*) FROM orders o
       WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.order_id)
UNION ALL
SELECT 'Orders outside Jan 2017 to Aug 2018 (partial months)',  SUM(substr(purchased_at, 1, 7) NOT BETWEEN '2017-01' AND '2018-08') FROM orders
UNION ALL
SELECT 'Delivered orders missing a delivery date',              SUM(status = 'delivered' AND delivered_at IS NULL) FROM orders
UNION ALL
SELECT 'Products with no category',                             SUM(category = 'unknown') FROM products
UNION ALL
SELECT 'Orders kept in the sales view',                         COUNT(*) FROM sales;
