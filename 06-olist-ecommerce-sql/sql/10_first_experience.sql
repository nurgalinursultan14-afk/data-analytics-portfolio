-- Q10. Does a bad first order make a customer less likely to come back?
-- First order per person via ROW_NUMBER(); "came back" = any later-day order (same rule as Q3).
-- Only first orders placed by Feb 2018 count, so everyone has 6+ months to return.
WITH ordered AS (
    SELECT customer_unique_id, purchased_at, is_late, review_score, status,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchased_at) AS n
    FROM sales
),
firsts AS (
    SELECT o.*,
           EXISTS (SELECT 1 FROM sales s
                   WHERE s.customer_unique_id = o.customer_unique_id
                     AND date(s.purchased_at) > date(o.purchased_at)) AS came_back
    FROM ordered o
    WHERE n = 1 AND status = 'delivered' AND purchased_at < '2018-03-01'
)
SELECT 'Delivery' AS factor,
       CASE is_late WHEN 1 THEN 'late' ELSE 'on time' END AS first_order,
       COUNT(*) AS customers,
       ROUND(100.0 * AVG(came_back), 2) AS pct_came_back
FROM firsts WHERE is_late IS NOT NULL GROUP BY 2
UNION ALL
SELECT 'Review',
       CASE WHEN review_score <= 2 THEN '1-2 stars' WHEN review_score = 3 THEN '3 stars' ELSE '4-5 stars' END,
       COUNT(*), ROUND(100.0 * AVG(came_back), 2)
FROM firsts WHERE review_score IS NOT NULL GROUP BY 2
ORDER BY factor, first_order;
