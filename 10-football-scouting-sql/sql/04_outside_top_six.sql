-- Q4. The realistic shortlist: the best wide forwards at clubs that finished 7th or lower,
-- the players a mid-table club could actually afford to approach.
WITH table_pos AS (
    SELECT team,
           RANK() OVER (ORDER BY SUM(CASE WHEN gf > ga THEN 3 WHEN gf = ga THEN 1 ELSE 0 END) DESC,
                                 SUM(gf - ga) DESC) AS position
    FROM (SELECT home_team AS team, home_score AS gf, away_score AS ga FROM matches
          UNION ALL SELECT away_team, away_score, home_score FROM matches)
    GROUP BY team
)
SELECT RANK() OVER (ORDER BY s.score DESC) AS rank,
       s.player, s.team, t.position AS club_finish, CAST(ROUND(s.minutes) AS INTEGER) AS minutes,
       s.score, s.np_xg_90, s.xa_90, s.dribbles_won_90, s.prog_carries_90
FROM wide_forward_scores s
JOIN table_pos t ON t.team = s.team
WHERE t.position >= 7
ORDER BY s.score DESC
LIMIT 8;
