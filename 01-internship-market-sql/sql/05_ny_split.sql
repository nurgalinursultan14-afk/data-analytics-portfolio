-- Q5. Inside New York State: NYC versus the rest of the state, plus remote-US postings for comparison.
SELECT CASE WHEN l.location IN ('NYC', 'New York, NY', 'Brooklyn, NY') THEN 'New York City'
            WHEN l.state = 'NY' THEN 'Rest of New York State'
            WHEN l.is_remote = 1 AND l.country = 'US' THEN 'Remote (US)'
       END AS area,
       s.category,
       COUNT(DISTINCT l.id) AS postings
FROM posting_locations l JOIN s27 s USING (id)
WHERE l.state = 'NY' OR (l.is_remote = 1 AND l.country = 'US')
GROUP BY area, s.category
ORDER BY area, postings DESC;
