-- Q3. Top 10 wide forwards by scouting score (all clubs).
SELECT RANK() OVER (ORDER BY score DESC) AS rank,
       player, team, CAST(ROUND(minutes) AS INTEGER) AS minutes,
       score, np_xg_90, xa_90, key_passes_90, dribbles_won_90, prog_carries_90, box_passes_90,
       np_goals, assists
FROM wide_forward_scores
ORDER BY score DESC
LIMIT 10;
