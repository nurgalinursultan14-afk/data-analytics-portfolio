-- Q6. Which application systems do employers use? Share of Summer 2027 postings per ATS and category.
SELECT category, ats,
       COUNT(*) AS postings,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY category), 1) AS pct_of_category
FROM s27
GROUP BY category, ats
ORDER BY category, postings DESC;
