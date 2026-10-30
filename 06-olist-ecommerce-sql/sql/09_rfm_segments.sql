-- Q9. RFM segmentation: Recency, Frequency, Monetary value.
-- Recency and monetary are scored 1-5 with NTILE(5); frequency is just 1 vs. 2+ purchase days,
-- because 97% of customers buy once and quintiles of a constant are meaningless.
-- "Today" is the day after the last order in the window.
WITH c AS (
    SELECT customer_unique_id,
           julianday((SELECT date(MAX(purchased_at), '+1 day') FROM sales))
             - julianday(MAX(purchased_at))        AS recency_days,
           COUNT(DISTINCT date(purchased_at))      AS frequency,     -- purchase days, as in Q3
           SUM(gmv)                                AS monetary
    FROM sales
    GROUP BY customer_unique_id
),
scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,   -- 5 = most recent
           NTILE(5) OVER (ORDER BY monetary)          AS m_score    -- 5 = biggest spender
    FROM c
),
segmented AS (
    SELECT *,
           CASE WHEN frequency >= 2 AND r_score >= 4           THEN '1) Active repeat buyers'
                WHEN frequency >= 2                            THEN '2) Lapsed repeat buyers'
                WHEN r_score >= 4 AND m_score >= 4             THEN '3) Recent one-time, high spend'
                WHEN r_score >= 4                              THEN '4) Recent one-time, low spend'
                WHEN m_score >= 4                              THEN '5) Lapsed one-time, high spend'
                ELSE                                                '6) Lapsed one-time, low spend'
           END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*)                                                 AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)       AS pct_customers,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_revenue,
       ROUND(AVG(recency_days))                                 AS avg_days_since_last,
       ROUND(AVG(monetary), 2)                                  AS avg_spend_brl
FROM segmented
GROUP BY segment
ORDER BY segment;
