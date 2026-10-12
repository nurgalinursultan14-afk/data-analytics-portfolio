-- Q3. How fast do Summer 2027 postings close?
-- Uses snapshots every 3 days from git history (status_history). Cohort: postings first seen
-- between Jun 18 and Sep 10, 2026, so every posting has at least 30 days of follow-up.
-- Percentiles via window functions because SQLite has no MEDIAN().
WITH cohort AS (
    SELECT s.category,
           julianday(COALESCE(h.first_closed, '2026-10-10')) - julianday(h.first_seen) AS days_open,
           h.first_closed IS NOT NULL AS closed
    FROM s27 s
    JOIN status_history h ON h.id = s.id
    WHERE h.first_seen BETWEEN '2026-06-18' AND '2026-09-10'
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY days_open) AS rn,
              COUNT(*)     OVER (PARTITION BY category)                    AS n
    FROM cohort
)
SELECT category,
       MAX(n)                                                              AS postings,
       ROUND(100.0 * SUM(closed AND days_open <= 7)  / MAX(n), 1)          AS pct_closed_within_7d,
       ROUND(100.0 * SUM(closed AND days_open <= 14) / MAX(n), 1)          AS pct_closed_within_14d,
       ROUND(100.0 * SUM(closed AND days_open <= 30) / MAX(n), 1)          AS pct_closed_within_30d,
       MAX(CASE WHEN rn = CAST(0.5 * n AS INT) + 1 THEN days_open END)     AS median_days_open
FROM ranked
GROUP BY category
ORDER BY median_days_open;
