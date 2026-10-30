-- Q2. Monthly orders, revenue (GMV) and average order value, with month-over-month growth.
-- LAG() looks one row back; the 3-month rolling average smooths out the November spike.
WITH monthly AS (
    SELECT purchase_month,
           COUNT(*)                      AS orders,
           COUNT(DISTINCT customer_unique_id) AS customers,
           ROUND(SUM(gmv), 0)            AS gmv_brl,
           ROUND(AVG(gmv), 2)            AS avg_order_value
    FROM sales
    GROUP BY purchase_month
)
SELECT purchase_month,
       orders,
       customers,
       gmv_brl,
       avg_order_value,
       ROUND(100.0 * (gmv_brl - LAG(gmv_brl) OVER w) / LAG(gmv_brl) OVER w, 1)   AS gmv_mom_pct,
       ROUND(AVG(gmv_brl) OVER (w ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0)   AS gmv_3mo_avg
FROM monthly
WINDOW w AS (ORDER BY purchase_month)
ORDER BY purchase_month;
