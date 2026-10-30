-- Q4. Daily rides with a 7-day rolling average and day-over-day change, next to the weather.
-- Window frames: AVG() OVER (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW); LAG() for the previous day.
WITH daily AS (
    SELECT start_date AS date, COUNT(*) AS rides
    FROM rides
    GROUP BY start_date
)
SELECT d.date,
       CASE strftime('%w', d.date) WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue'
            WHEN '3' THEN 'Wed' WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END   AS dow,
       d.rides,
       ROUND(AVG(d.rides) OVER (ORDER BY d.date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW))  AS rolling_7d_avg,
       ROUND(100.0 * (d.rides - LAG(d.rides) OVER (ORDER BY d.date))
             / LAG(d.rides) OVER (ORDER BY d.date), 1)                                       AS pct_change_vs_prev_day,
       w.tmax_f,
       w.precip_in
FROM daily d
LEFT JOIN weather_daily w ON w.date = d.date
ORDER BY d.date;
