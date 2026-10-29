-- Q2. Who rides, on what, and for how long?
-- Median via ROW_NUMBER() because SQLite has no MEDIAN() / PERCENTILE_CONT().
WITH ranked AS (
    SELECT member_casual, rideable_type, duration_min, distance_km,
           ROW_NUMBER() OVER (PARTITION BY member_casual, rideable_type ORDER BY duration_min) AS rn,
           COUNT(*)     OVER (PARTITION BY member_casual, rideable_type)                       AS n
    FROM rides
)
SELECT member_casual,
       rideable_type,
       MAX(n)                                                         AS rides,
       ROUND(100.0 * MAX(n) / (SELECT COUNT(*) FROM rides), 1)        AS pct_of_all_rides,
       MAX(CASE WHEN rn = n / 2 + 1 THEN duration_min END)            AS median_minutes,
       ROUND(AVG(distance_km), 2)                                     AS avg_km_straight_line
FROM ranked
GROUP BY member_casual, rideable_type
ORDER BY rides DESC;
