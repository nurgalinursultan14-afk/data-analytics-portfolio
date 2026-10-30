-- Q5. How much does a late delivery hurt the review score?
-- Lateness = delivered date minus the date promised at checkout, bucketed with CASE.
WITH delivered AS (
    SELECT review_score,
           julianday(date(delivered_at)) - julianday(date(estimated_delivery)) AS days_late
    FROM sales
    WHERE status = 'delivered' AND delivered_at IS NOT NULL AND review_score IS NOT NULL
)
SELECT CASE WHEN days_late <= -7 THEN '1) 7+ days early'
            WHEN days_late <= 0  THEN '2) 0-6 days early'
            WHEN days_late <= 3  THEN '3) 1-3 days late'
            WHEN days_late <= 7  THEN '4) 4-7 days late'
            ELSE                      '5) 8+ days late' END                AS delivery,
       COUNT(*)                                                           AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                 AS pct_of_orders,
       ROUND(AVG(review_score), 2)                                        AS avg_stars,
       ROUND(100.0 * SUM(review_score = 1) / COUNT(*), 1)                 AS pct_1_star,
       ROUND(100.0 * SUM(review_score = 5) / COUNT(*), 1)                 AS pct_5_star
FROM delivered
GROUP BY delivery
ORDER BY delivery;
