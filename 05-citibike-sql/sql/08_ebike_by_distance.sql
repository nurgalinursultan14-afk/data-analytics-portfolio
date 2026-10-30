-- Q8. Do riders pick e-bikes for longer trips?
-- Bucket trips by straight-line distance and compute the e-bike share in each bucket.
WITH bucketed AS (
    SELECT rideable_type,
           CASE WHEN distance_km < 1 THEN '1) under 1 km'
                WHEN distance_km < 2 THEN '2) 1-2 km'
                WHEN distance_km < 3 THEN '3) 2-3 km'
                WHEN distance_km < 5 THEN '4) 3-5 km'
                ELSE                      '5) 5 km or more' END AS distance_band
    FROM rides
    WHERE distance_km > 0          -- excludes round trips, where start = end
)
SELECT distance_band,
       COUNT(*)                                                           AS rides,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                 AS pct_of_rides,
       ROUND(100.0 * SUM(rideable_type = 'electric_bike') / COUNT(*), 1)  AS pct_ebike
FROM bucketed
GROUP BY distance_band
ORDER BY distance_band;
