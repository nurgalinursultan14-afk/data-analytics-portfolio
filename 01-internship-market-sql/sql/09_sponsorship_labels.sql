-- Q9. How often do postings state their sponsorship stance? (All terms.)
SELECT sponsorship,
       COUNT(*) AS postings,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM postings), 2) AS pct
FROM postings
GROUP BY sponsorship
ORDER BY postings DESC;
