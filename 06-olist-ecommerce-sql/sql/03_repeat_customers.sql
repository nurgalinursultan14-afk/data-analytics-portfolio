-- Q3. How many customers ever come back?
-- A "repeat" must be on a later calendar day than the first order: some people check out
-- the same basket as two orders minutes apart, which is not a return visit.
WITH ordered AS (
    SELECT customer_unique_id,
           date(purchased_at) AS order_date,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchased_at) AS n
    FROM sales
),
firsts AS (
    SELECT customer_unique_id, order_date AS first_date FROM ordered WHERE n = 1
),
returns AS (
    SELECT f.customer_unique_id,
           MIN(julianday(o.order_date) - julianday(f.first_date)) AS days_to_return
    FROM firsts f
    JOIN ordered o ON o.customer_unique_id = f.customer_unique_id AND o.order_date > f.first_date
    GROUP BY f.customer_unique_id
),
ranked AS (
    SELECT days_to_return,
           ROW_NUMBER() OVER (ORDER BY days_to_return) AS rn,
           COUNT(*) OVER ()                            AS n
    FROM returns
)
SELECT (SELECT COUNT(*) FROM firsts)                                          AS customers,
       (SELECT COUNT(*) FROM returns)                                         AS came_back_later,
       ROUND(100.0 * (SELECT COUNT(*) FROM returns) / (SELECT COUNT(*) FROM firsts), 2) AS repeat_rate_pct,
       (SELECT COUNT(DISTINCT customer_unique_id) FROM ordered WHERE n > 1)
         - (SELECT COUNT(*) FROM returns)                                     AS same_day_only_multi_order,
       (SELECT days_to_return FROM ranked WHERE rn = n / 2 + 1)               AS median_days_to_return,
       ROUND(100.0 * (SELECT COUNT(*) FROM returns WHERE days_to_return <= 90)
             / (SELECT COUNT(*) FROM returns), 1)                             AS pct_returns_within_90d;
