-- Q6. What kind of wide forward is each top-10 player? The metric each one ranks highest
-- on in the pool, with that percentile.
WITH top AS (SELECT * FROM wide_forward_scores ORDER BY score DESC LIMIT 10),
long AS (
    SELECT player, team, score, 'shooting (np xG)' AS strength, p_np_xg AS pct FROM top
    UNION ALL SELECT player, team, score, 'chance creation (xA)', p_xa FROM top
    UNION ALL SELECT player, team, score, 'key passes', p_key_passes FROM top
    UNION ALL SELECT player, team, score, 'dribbling', p_dribbles FROM top
    UNION ALL SELECT player, team, score, 'carrying the ball forward', p_prog_carries FROM top
    UNION ALL SELECT player, team, score, 'passes into the box', p_box_passes FROM top
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY player, team ORDER BY pct DESC, strength) AS rn FROM long
)
SELECT player, team, score, strength AS top_strength, pct AS percentile
FROM ranked WHERE rn = 1
ORDER BY score DESC;
