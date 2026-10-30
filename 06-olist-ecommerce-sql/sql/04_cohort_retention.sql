-- Q4. Cohort retention: of the customers who first bought in month M, what share bought
-- again 1, 2, 3, 6 and 12 months later?
-- Month offsets come from year*12 + month arithmetic; conditional aggregation pivots them
-- into columns. A cohort shows NULL where that month is past the end of the data (Aug 2018).
WITH first_month AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort
    FROM sales GROUP BY customer_unique_id
),
activity AS (
    SELECT DISTINCT s.customer_unique_id, f.cohort,
           (CAST(substr(s.purchase_month, 1, 4) AS INT) * 12 + CAST(substr(s.purchase_month, 6, 2) AS INT))
         - (CAST(substr(f.cohort, 1, 4) AS INT) * 12 + CAST(substr(f.cohort, 6, 2) AS INT)) AS month_offset
    FROM sales s JOIN first_month f USING (customer_unique_id)
),
cohort_size AS (
    SELECT cohort, COUNT(*) AS customers FROM first_month GROUP BY cohort
),
months_left AS (
    SELECT cohort,
           (2018 * 12 + 8) - (CAST(substr(cohort, 1, 4) AS INT) * 12 + CAST(substr(cohort, 6, 2) AS INT)) AS max_offset
    FROM cohort_size
)
SELECT a.cohort,
       z.customers,
       CASE WHEN m.max_offset >= 1  THEN ROUND(100.0 * SUM(a.month_offset = 1)  / z.customers, 2) END AS m1_pct,
       CASE WHEN m.max_offset >= 2  THEN ROUND(100.0 * SUM(a.month_offset = 2)  / z.customers, 2) END AS m2_pct,
       CASE WHEN m.max_offset >= 3  THEN ROUND(100.0 * SUM(a.month_offset = 3)  / z.customers, 2) END AS m3_pct,
       CASE WHEN m.max_offset >= 6  THEN ROUND(100.0 * SUM(a.month_offset = 6)  / z.customers, 2) END AS m6_pct,
       CASE WHEN m.max_offset >= 12 THEN ROUND(100.0 * SUM(a.month_offset = 12) / z.customers, 2) END AS m12_pct,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN a.month_offset >= 1 THEN a.customer_unique_id END)
             / z.customers, 2)                                                                   AS ever_returned_pct
FROM activity a
JOIN cohort_size z USING (cohort)
JOIN months_left m USING (cohort)
GROUP BY a.cohort
ORDER BY a.cohort;
