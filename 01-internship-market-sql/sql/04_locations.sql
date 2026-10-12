-- Q4. Where are Summer 2027 US internships? Distinct postings per state (multi-city postings count once per state).
SELECT state,
       COUNT(DISTINCT l.id) AS postings,
       ROUND(100.0 * COUNT(DISTINCT l.id) /
             (SELECT COUNT(DISTINCT l2.id) FROM posting_locations l2 JOIN s27 USING (id)
              WHERE l2.country = 'US'), 1) AS pct_of_us_postings
FROM posting_locations l JOIN s27 USING (id)
WHERE l.state IS NOT NULL
GROUP BY state
ORDER BY postings DESC
LIMIT 15;
