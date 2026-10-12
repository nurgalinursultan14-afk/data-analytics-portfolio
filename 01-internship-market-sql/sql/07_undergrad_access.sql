-- Q7. How many Summer 2027 postings are open to undergraduates?
-- 'Open' = lists Bachelor's, or lists no degree requirement at all.
SELECT s.category,
       COUNT(*) AS postings,
       SUM(CASE WHEN EXISTS (SELECT 1 FROM posting_degrees d WHERE d.id = s.id AND d.degree = 'Bachelor''s')
                  OR NOT EXISTS (SELECT 1 FROM posting_degrees d WHERE d.id = s.id)
                THEN 1 ELSE 0 END) AS open_to_undergrads,
       SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM posting_degrees d WHERE d.id = s.id AND d.degree = 'Bachelor''s')
                 AND EXISTS (SELECT 1 FROM posting_degrees d WHERE d.id = s.id)
                THEN 1 ELSE 0 END) AS graduate_only
FROM s27 s
GROUP BY s.category
ORDER BY postings DESC;
