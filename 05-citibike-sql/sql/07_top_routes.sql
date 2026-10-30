-- Q7. The most popular routes: weekday members vs. weekend casual riders.
-- Self-join of the stations dimension (once for start, once for end) to label each route.
WITH routes AS (
    SELECT CASE WHEN member_casual = 'member'
                 AND strftime('%w', start_date) NOT IN ('0', '6') AND start_date <> '2026-09-07'
                THEN 'member, weekday'
                WHEN member_casual = 'casual'
                 AND (strftime('%w', start_date) IN ('0', '6') OR start_date = '2026-09-07')
                THEN 'casual, weekend/holiday' END AS segment,
           start_station_id, end_station_id
    FROM rides
    WHERE start_station_id IS NOT NULL AND end_station_id IS NOT NULL
),
counted AS (
    SELECT segment, start_station_id, end_station_id, COUNT(*) AS rides,
           ROW_NUMBER() OVER (PARTITION BY segment ORDER BY COUNT(*) DESC) AS rn
    FROM routes
    WHERE segment IS NOT NULL
    GROUP BY segment, start_station_id, end_station_id
)
SELECT c.segment,
       c.rn                                          AS rank,
       s1.name                                       AS from_station,
       CASE WHEN c.start_station_id = c.end_station_id THEN '(round trip)' ELSE s2.name END AS to_station,
       c.rides
FROM counted c
JOIN stations s1 ON s1.station_id = c.start_station_id
JOIN stations s2 ON s2.station_id = c.end_station_id
WHERE c.rn <= 10
ORDER BY c.segment DESC, c.rn;
