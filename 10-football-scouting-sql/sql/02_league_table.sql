-- Q2. Final league table, built from the 380 results (3 points a win, 1 a draw).
WITH results AS (
    SELECT home_team AS team, home_score AS gf, away_score AS ga FROM matches
    UNION ALL
    SELECT away_team, away_score, home_score FROM matches
)
SELECT RANK() OVER (ORDER BY SUM(CASE WHEN gf > ga THEN 3 WHEN gf = ga THEN 1 ELSE 0 END) DESC,
                             SUM(gf - ga) DESC) AS position,
       team,
       COUNT(*) AS played,
       SUM(gf > ga) AS won, SUM(gf = ga) AS drawn, SUM(gf < ga) AS lost,
       SUM(gf) AS goals_for, SUM(ga) AS goals_against,
       SUM(CASE WHEN gf > ga THEN 3 WHEN gf = ga THEN 1 ELSE 0 END) AS points
FROM results
GROUP BY team
ORDER BY position;
