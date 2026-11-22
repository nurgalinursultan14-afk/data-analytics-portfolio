-- Q1. Is the data complete and do the minutes add up?
SELECT 'matches' AS check_name, COUNT(*) AS value FROM matches
UNION ALL SELECT 'events kept (shots, passes, carries, dribbles, recoveries, interceptions)', COUNT(*) FROM events
UNION ALL SELECT 'goals in final scores', SUM(home_score + away_score) FROM matches
UNION ALL SELECT 'goals scored from shots (the rest are own goals)', COUNT(*) FROM events WHERE type = 'Shot' AND outcome = 'Goal'
UNION ALL SELECT 'shots whose key pass is missing', COUNT(*)
    FROM events s LEFT JOIN events p ON p.event_id = s.key_pass_id
    WHERE s.type = 'Shot' AND s.key_pass_id IS NOT NULL AND p.event_id IS NULL
UNION ALL SELECT 'player minutes per team per match (11 x ~94 expected)',
    ROUND(SUM(MAX(end_min - start_min, 0)) / COUNT(DISTINCT match_id || team), 0) FROM spells
UNION ALL SELECT 'lineup spells that end before they start (counted as 0)', COUNT(*) FROM spells WHERE end_min < start_min
UNION ALL SELECT 'players with any minutes', COUNT(DISTINCT player_id) FROM player_minutes
UNION ALL SELECT 'wide forwards in the scouting pool (900+ wide minutes)', COUNT(*) FROM wide_forwards;
