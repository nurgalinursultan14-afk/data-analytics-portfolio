-- Q6. Which stations empty out or fill up during the weekday morning rush (7:00-9:59)?
-- Net flow = arrivals - departures. Big negatives are where riders find no bikes; big positives
-- are where they find no free docks. This is the problem Citi Bike's rebalancing vans solve.
WITH am AS (
    SELECT * FROM rides
    WHERE start_hour BETWEEN 7 AND 9
      AND strftime('%w', start_date) NOT IN ('0', '6')
      AND start_date <> '2026-09-07'
),
weekdays AS (SELECT COUNT(DISTINCT start_date) AS n FROM am),
flows AS (
    SELECT station_id, SUM(departures) AS departures, SUM(arrivals) AS arrivals
    FROM (
        SELECT start_station_id AS station_id, 1 AS departures, 0 AS arrivals FROM am
        WHERE start_station_id IS NOT NULL
        UNION ALL
        SELECT end_station_id, 0, 1 FROM am
        WHERE end_station_id IS NOT NULL
    )
    GROUP BY station_id
),
ranked AS (
    SELECT f.*,
           RANK() OVER (ORDER BY arrivals - departures)      AS drain_rank,
           RANK() OVER (ORDER BY arrivals - departures DESC) AS fill_rank
    FROM flows f
)
SELECT CASE WHEN r.drain_rank <= 10 THEN 'empties out' ELSE 'fills up' END     AS pattern,
       s.name                                                                   AS station,
       ROUND(1.0 * r.departures / w.n, 1)                                       AS avg_departures_per_morning,
       ROUND(1.0 * r.arrivals / w.n, 1)                                         AS avg_arrivals_per_morning,
       ROUND(1.0 * (r.arrivals - r.departures) / w.n, 1)                        AS net_bikes_per_morning,
       ROUND(s.lat, 4) AS lat, ROUND(s.lng, 4) AS lng
FROM ranked r
JOIN stations s ON s.station_id = r.station_id
CROSS JOIN weekdays w
WHERE r.drain_rank <= 10 OR r.fill_rank <= 10
ORDER BY net_bikes_per_morning;
