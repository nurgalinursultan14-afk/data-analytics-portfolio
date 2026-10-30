-- Q7. Which product categories drive revenue, and how satisfied are their buyers?
-- Item-level revenue (price only, no freight) joined to products; reviews are per order, so
-- an order with items in two categories counts toward both categories' ratings.
WITH cat AS (
    SELECT p.category,
           COUNT(DISTINCT i.order_id)                 AS orders,
           SUM(i.price)                               AS revenue,
           AVG(i.freight / i.price)                   AS freight_ratio
    FROM order_items i
    JOIN sales s    ON s.order_id = i.order_id
    JOIN products p ON p.product_id = i.product_id
    GROUP BY p.category
),
cat_reviews AS (
    SELECT p.category, AVG(s.review_score) AS avg_stars
    FROM (SELECT DISTINCT i.order_id, p.category FROM order_items i JOIN products p USING (product_id)) p
    JOIN sales s ON s.order_id = p.order_id
    GROUP BY p.category
)
SELECT RANK() OVER (ORDER BY c.revenue DESC)                      AS rank,
       c.category,
       c.orders,
       ROUND(c.revenue)                                           AS revenue_brl,
       ROUND(100.0 * c.revenue / SUM(c.revenue) OVER (), 1)       AS pct_of_revenue,
       ROUND(100.0 * SUM(c.revenue) OVER (ORDER BY c.revenue DESC)
             / SUM(c.revenue) OVER (), 1)                          AS cumulative_pct,
       ROUND(r.avg_stars, 2)                                      AS avg_stars,
       ROUND(100.0 * c.freight_ratio, 1)                          AS freight_pct_of_price
FROM cat c
JOIN cat_reviews r USING (category)
ORDER BY c.revenue DESC
LIMIT 15;
