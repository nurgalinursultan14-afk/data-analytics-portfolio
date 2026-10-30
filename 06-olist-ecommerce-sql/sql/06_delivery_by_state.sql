-- Q6. Which states wait longest, and how often are they let down?
-- Median delivery days per state via ROW_NUMBER(); only states with 500+ delivered orders.
WITH d AS (
    SELECT customer_state, days_to_deliver, is_late,
           julianday(date(estimated_delivery)) - julianday(date(purchased_at)) AS days_promised,
           ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY days_to_deliver) AS rn,
           COUNT(*)     OVER (PARTITION BY customer_state)                         AS n
    FROM sales
    WHERE status = 'delivered' AND delivered_at IS NOT NULL
)
SELECT customer_state,
       MAX(n)                                                    AS delivered_orders,
       MAX(CASE WHEN rn = n / 2 + 1 THEN days_to_deliver END)    AS median_days_to_deliver,
       ROUND(AVG(days_promised), 1)                              AS avg_days_promised,
       ROUND(100.0 * AVG(is_late), 1)                            AS pct_late
FROM d
GROUP BY customer_state
HAVING MAX(n) >= 500
ORDER BY pct_late DESC;
