-- Q9. Where do casual (non-member) riders start? Stations with the highest casual share.
-- HAVING keeps only busy stations so small stations with a handful of rides don't top the list.
SELECT s.name                                                      AS station,
       COUNT(*)                                                    AS departures,
       SUM(r.member_casual = 'casual')                             AS casual_departures,
       ROUND(100.0 * SUM(r.member_casual = 'casual') / COUNT(*), 1) AS pct_casual,
       ROUND(100.0 * SUM(r.start_station_id = r.end_station_id) / COUNT(*), 1) AS pct_round_trips
FROM rides r
JOIN stations s ON s.station_id = r.start_station_id
GROUP BY s.station_id, s.name
HAVING COUNT(*) >= 3000
ORDER BY pct_casual DESC
LIMIT 15;
