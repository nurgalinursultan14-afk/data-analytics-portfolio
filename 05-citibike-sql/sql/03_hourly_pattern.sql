-- Q3. When during the day do members and casual riders ride?
-- Labor Day (Mon Sep 7) is grouped with weekends because ridership behaves like a weekend.
-- Each hour is shown as a % of that group's daily rides so weekday and weekend are comparable.
WITH labeled AS (
    SELECT member_casual,
           start_hour,
           CASE WHEN strftime('%w', start_date) IN ('0', '6') OR start_date = '2026-09-07'
                THEN 'weekend/holiday' ELSE 'weekday' END AS day_type
    FROM rides
),
counts AS (
    SELECT day_type, member_casual, start_hour, COUNT(*) AS rides
    FROM labeled
    GROUP BY day_type, member_casual, start_hour
)
SELECT day_type,
       member_casual,
       start_hour,
       rides,
       ROUND(100.0 * rides / SUM(rides) OVER (PARTITION BY day_type, member_casual), 2) AS pct_of_group
FROM counts
ORDER BY day_type, member_casual, start_hour;
