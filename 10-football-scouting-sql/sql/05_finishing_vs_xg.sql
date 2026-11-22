-- Q5. Who scored more or fewer than their chances were worth? Non-penalty goals minus
-- non-penalty xG for the pool. A big gap is usually luck or a hot streak, not skill.
SELECT player, team, np_goals, np_xg,
       ROUND(np_goals - np_xg, 1) AS goals_minus_xg
FROM wide_forwards
WHERE np_goals + np_xg >= 3
ORDER BY goals_minus_xg DESC;
