-- Typed, cleaned tables from the all-text staging tables that build_db.py loads.
-- StatsBomb pitch: 120 x 80 yards, attacking left to right (x = 120 is the opponent's goal line).

CREATE TABLE matches AS
SELECT CAST(match_id AS INTEGER) AS match_id,
       DATE(match_date)          AS match_date,
       home_team, away_team,
       CAST(home_score AS INTEGER) AS home_score,
       CAST(away_score AS INTEGER) AS away_score
FROM raw_matches;

CREATE TABLE events AS
SELECT event_id,
       CAST(match_id AS INTEGER)  AS match_id,
       CAST(period AS INTEGER)    AS period,
       CAST(minute AS INTEGER)    AS minute,
       type, team,
       CAST(player_id AS INTEGER) AS player_id,
       player,
       CAST(x AS REAL) AS x, CAST(y AS REAL) AS y,
       CAST(end_x AS REAL) AS end_x, CAST(end_y AS REAL) AS end_y,
       outcome,                              -- passes: NULL = completed
       CAST(xg AS REAL) AS xg,
       shot_type, key_pass_id,
       CAST(shot_assist AS INTEGER) AS shot_assist,
       CAST(goal_assist AS INTEGER) AS goal_assist,
       CAST(is_cross AS INTEGER)    AS is_cross
FROM raw_events
WHERE player_id IS NOT NULL;

CREATE INDEX ix_events_player ON events (player_id, type);
CREATE INDEX ix_events_id ON events (event_id);

-- Minutes per lineup spell. The clock is "MM:SS" on a running match clock (the second half
-- starts at 45:00). A spell with no end ran to the final whistle: the last event minute of
-- the match. A few spells in the source end before they start; they count as 0 minutes
-- (01_data_quality.sql counts them).
CREATE TABLE spells AS
WITH match_end AS (
    SELECT CAST(match_id AS INTEGER) AS match_id, MAX(CAST(last_minute AS REAL)) AS end_min
    FROM raw_period_end GROUP BY match_id
)
SELECT CAST(s.match_id AS INTEGER) AS match_id,
       s.team,
       CAST(s.player_id AS INTEGER) AS player_id,
       s.player,
       s.position,
       CAST(substr(s.from_clock, 1, instr(s.from_clock, ':') - 1) AS REAL)
         + CAST(substr(s.from_clock, instr(s.from_clock, ':') + 1) AS REAL) / 60 AS start_min,
       CASE WHEN s.to_clock IS NULL THEN e.end_min
            ELSE CAST(substr(s.to_clock, 1, instr(s.to_clock, ':') - 1) AS REAL)
                 + CAST(substr(s.to_clock, instr(s.to_clock, ':') + 1) AS REAL) / 60 END AS end_min
FROM raw_spells s
JOIN match_end e ON e.match_id = CAST(s.match_id AS INTEGER);

-- Wide forwards: wingers and wide midfielders, the position this shortlist is for.
CREATE TABLE player_minutes AS
SELECT player_id,
       player,
       team,
       ROUND(SUM(MAX(end_min - start_min, 0)), 1) AS minutes,
       ROUND(SUM(CASE WHEN position IN ('Right Wing', 'Left Wing', 'Right Midfield', 'Left Midfield')
                      THEN MAX(end_min - start_min, 0) ELSE 0 END), 1) AS wide_minutes,
       COUNT(DISTINCT match_id) AS matches
FROM spells
GROUP BY player_id, team;

-- Season totals per player and team for the actions this project scores.
CREATE VIEW player_actions AS
SELECT e.player_id,
       e.team,
       SUM(CASE WHEN e.type = 'Shot' AND e.shot_type <> 'Penalty' THEN e.xg ELSE 0 END)        AS np_xg,
       SUM(CASE WHEN e.type = 'Shot' AND e.shot_type <> 'Penalty' THEN 1 ELSE 0 END)           AS np_shots,
       SUM(CASE WHEN e.type = 'Shot' AND e.outcome = 'Goal' AND e.shot_type <> 'Penalty' THEN 1 ELSE 0 END) AS np_goals,
       SUM(CASE WHEN e.type = 'Pass' AND (e.shot_assist = 1 OR e.goal_assist = 1) THEN 1 ELSE 0 END) AS key_passes,
       SUM(CASE WHEN e.type = 'Pass' AND e.goal_assist = 1 THEN 1 ELSE 0 END)                  AS assists,
       SUM(CASE WHEN e.type = 'Dribble' AND e.outcome = 'Complete' THEN 1 ELSE 0 END)           AS dribbles_won,
       SUM(CASE WHEN e.type = 'Dribble' THEN 1 ELSE 0 END)                                    AS dribbles,
       -- Progressive carry: moves the ball 10+ yards toward goal and ends in the opponent's half.
       SUM(CASE WHEN e.type = 'Carry' AND e.end_x - e.x >= 10 AND e.end_x >= 60 THEN 1 ELSE 0 END) AS prog_carries,
       -- Completed pass from outside the penalty area into it (box: x >= 102, 18 <= y <= 62).
       SUM(CASE WHEN e.type = 'Pass' AND e.outcome IS NULL
                 AND e.end_x >= 102 AND e.end_y BETWEEN 18 AND 62
                 AND NOT (e.x >= 102 AND e.y BETWEEN 18 AND 62) THEN 1 ELSE 0 END)            AS box_passes,
       SUM(CASE WHEN e.type IN ('Ball Recovery', 'Interception') AND e.x >= 80 THEN 1 ELSE 0 END) AS high_recoveries
FROM events e
GROUP BY e.player_id, e.team;

-- Expected assists: the non-penalty xG of every shot a player's pass set up.
CREATE VIEW player_xa AS
SELECT p.player_id, p.team, SUM(s.xg) AS xa
FROM events s
JOIN events p ON p.event_id = s.key_pass_id
WHERE s.type = 'Shot' AND s.shot_type <> 'Penalty'
GROUP BY p.player_id, p.team;

-- The scouting pool: 900+ minutes as a wide forward, and at least 60% of their minutes there,
-- with every action per 90 minutes. Per-90 rates use all of the player's minutes and actions
-- for that team, since events are not tagged with the position the player held at the time.
CREATE VIEW wide_forwards AS
SELECT m.player_id, m.player, m.team, m.matches,
       m.minutes, m.wide_minutes,
       ROUND(a.np_xg * 90 / m.minutes, 3)            AS np_xg_90,
       ROUND(COALESCE(x.xa, 0) * 90 / m.minutes, 3)  AS xa_90,
       ROUND(a.key_passes * 90.0 / m.minutes, 2)     AS key_passes_90,
       ROUND(a.dribbles_won * 90.0 / m.minutes, 2)   AS dribbles_won_90,
       ROUND(a.prog_carries * 90.0 / m.minutes, 2)   AS prog_carries_90,
       ROUND(a.box_passes * 90.0 / m.minutes, 2)     AS box_passes_90,
       ROUND(a.high_recoveries * 90.0 / m.minutes, 2) AS high_recoveries_90,
       a.np_goals, a.assists, ROUND(a.np_xg, 1) AS np_xg, ROUND(COALESCE(x.xa, 0), 1) AS xa
FROM player_minutes m
JOIN player_actions a ON a.player_id = m.player_id AND a.team = m.team
LEFT JOIN player_xa x ON x.player_id = m.player_id AND x.team = m.team
WHERE m.wide_minutes >= 900 AND m.wide_minutes >= 0.6 * m.minutes;

-- Each per-90 metric as a percentile within the pool (0 = lowest, 100 = highest), and the
-- scouting score: the plain average of the six attacking percentiles. Equal weights on
-- purpose; run_analysis.py tests how much the top 10 moves when the weights change.
CREATE VIEW wide_forward_scores AS
WITH pct AS (
    SELECT *,
           ROUND(100 * PERCENT_RANK() OVER (ORDER BY np_xg_90), 0)        AS p_np_xg,
           ROUND(100 * PERCENT_RANK() OVER (ORDER BY xa_90), 0)           AS p_xa,
           ROUND(100 * PERCENT_RANK() OVER (ORDER BY key_passes_90), 0)   AS p_key_passes,
           ROUND(100 * PERCENT_RANK() OVER (ORDER BY dribbles_won_90), 0) AS p_dribbles,
           ROUND(100 * PERCENT_RANK() OVER (ORDER BY prog_carries_90), 0) AS p_prog_carries,
           ROUND(100 * PERCENT_RANK() OVER (ORDER BY box_passes_90), 0)   AS p_box_passes
    FROM wide_forwards
)
SELECT *,
       ROUND((p_np_xg + p_xa + p_key_passes + p_dribbles + p_prog_carries + p_box_passes) / 6.0, 1) AS score
FROM pct;
