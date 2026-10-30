-- Q8. How concentrated is revenue among sellers? (A Pareto / "80-20" check.)
-- Running SUM() OVER (ORDER BY revenue DESC) gives each seller's cumulative share;
-- NTILE(100) puts sellers into percentiles by revenue.
WITH s AS (
    SELECT i.seller_id, SUM(i.price) AS revenue
    FROM order_items i JOIN sales x ON x.order_id = i.order_id
    GROUP BY i.seller_id
),
ranked AS (
    SELECT seller_id, revenue,
           NTILE(100) OVER (ORDER BY revenue DESC)        AS pctile,
           SUM(revenue) OVER ()                           AS total
    FROM s
)
SELECT top_pct                                            AS top_sellers_pct,
       SUM(CASE WHEN pctile <= top_pct THEN 1 END)       AS sellers,
       ROUND(100.0 * SUM(CASE WHEN pctile <= top_pct THEN revenue END) / MAX(total), 1) AS pct_of_revenue
FROM ranked
CROSS JOIN (SELECT 1 AS top_pct UNION ALL SELECT 5 UNION ALL SELECT 10
            UNION ALL SELECT 20 UNION ALL SELECT 50)
GROUP BY top_pct
ORDER BY top_pct;
