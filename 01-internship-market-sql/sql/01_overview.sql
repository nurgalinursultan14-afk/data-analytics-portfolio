-- Q1. How big is the Summer 2027 market so far, and how much of it is still open?
SELECT category,
       COUNT(*)                                   AS postings,
       SUM(active)                                AS still_open,
       ROUND(100.0 * SUM(active) / COUNT(*), 1)   AS pct_open,
       COUNT(DISTINCT company)                    AS companies
FROM s27
GROUP BY category
ORDER BY postings DESC;
