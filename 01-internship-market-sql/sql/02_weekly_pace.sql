-- Q2. When do Summer 2027 postings appear? New postings per week (week starting Monday).
SELECT date(date_posted, 'weekday 0', '-6 days') AS week_start,
       category,
       COUNT(*) AS new_postings
FROM s27
WHERE date_posted >= '2026-06-01'
GROUP BY week_start, category
ORDER BY week_start, category;
