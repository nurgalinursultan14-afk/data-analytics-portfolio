-- Q8. Which employers post the most analyst-type Summer 2027 roles in New York or remote-US?
WITH matches AS (
    SELECT DISTINCT s.id, s.company, s.active, s.ats
    FROM s27 s JOIN posting_locations l USING (id)
    WHERE (l.state = 'NY' OR (l.is_remote = 1 AND l.country = 'US'))
      AND (s.title LIKE '%analy%' OR s.title LIKE '%insight%' OR s.title LIKE '%business intelligence%'
           OR s.title LIKE '%data scien%' OR s.title LIKE '%research%' OR s.title LIKE '%operations%')
      AND s.title NOT LIKE '%engineer%'
)
SELECT company,
       COUNT(*)                  AS analyst_postings,
       SUM(active)               AS still_open,
       GROUP_CONCAT(DISTINCT ats) AS ats_used
FROM matches
GROUP BY company
ORDER BY analyst_postings DESC, company
LIMIT 15;
