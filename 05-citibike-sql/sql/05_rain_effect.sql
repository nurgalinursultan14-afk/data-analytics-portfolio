-- Q5. How much does rain cut ridership, and does it hit members or casual riders harder?
-- Wet day = at least 0.10 in of rain in Central Park that calendar day.
-- Each wet day is compared with the average of the DRY days on the same weekday, so a rainy
-- Sunday is compared with dry Sundays, not with busy Wednesdays. Labor Day (Mon Sep 7) is
-- left out of the baselines because it behaves like a weekend.
WITH daily AS (
    SELECT r.start_date                                  AS date,
           strftime('%w', r.start_date)                  AS dow,
           w.precip_in,
           SUM(r.member_casual = 'member')               AS member_rides,
           SUM(r.member_casual = 'casual')               AS casual_rides
    FROM rides r
    JOIN weather_daily w ON w.date = r.start_date
    GROUP BY r.start_date
),
baseline AS (
    SELECT dow, COUNT(*) AS dry_days,
           AVG(member_rides) AS member_base, AVG(casual_rides) AS casual_base
    FROM daily
    WHERE precip_in < 0.10 AND date <> '2026-09-07'
    GROUP BY dow
)
SELECT d.date,
       CASE d.dow WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue' WHEN '3' THEN 'Wed'
                  WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END              AS dow,
       d.precip_in,
       b.dry_days                                                                   AS baseline_days,
       d.member_rides,
       ROUND(100.0 * (d.member_rides - b.member_base) / b.member_base, 1)           AS member_pct_vs_dry,
       d.casual_rides,
       ROUND(100.0 * (d.casual_rides - b.casual_base) / b.casual_base, 1)           AS casual_pct_vs_dry
FROM daily d
JOIN baseline b ON b.dow = d.dow
WHERE d.precip_in >= 0.10
ORDER BY d.precip_in DESC;
