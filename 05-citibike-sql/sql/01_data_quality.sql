-- Q1. How clean is the raw trip file, and how many rows does the analysis keep?
-- Every check is one row so the result reads like a data-quality report.
WITH t AS (SELECT * FROM trips)
SELECT 'Raw trips in the September file'                         AS check_name, COUNT(*) AS trips FROM t
UNION ALL
SELECT 'Started Aug 31 (spillover from previous month)', SUM(start_date < '2026-09-01')        FROM t
UNION ALL
SELECT 'Shorter than 1 minute (Citi Bike already drops these)', SUM(duration_min < 1)        FROM t
UNION ALL
SELECT 'Longer than 3 hours',              SUM(duration_min > 180)                              FROM t
UNION ALL
SELECT 'No start station (e-bike parked off-dock)', SUM(start_station_id IS NULL)              FROM t
UNION ALL
SELECT 'No end station (bike not re-docked)',       SUM(end_station_id IS NULL)                FROM t
UNION ALL
SELECT 'To or from a repair shop / depot station',
       SUM(start_station_id IN (SELECT station_id FROM stations WHERE kind = 'system')
           OR end_station_id IN (SELECT station_id FROM stations WHERE kind = 'system')) FROM t
UNION ALL
SELECT 'Coordinates missing or outside NYC',        SUM(distance_km IS NULL)                   FROM t
UNION ALL
SELECT 'Kept in the rides view',           (SELECT COUNT(*) FROM rides);
