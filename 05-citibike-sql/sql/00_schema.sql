-- Star schema: one fact table (trips) and two dimensions (stations, weather_daily).
-- build_db.py loads the raw CSVs into raw_trips / raw_weather, then this file
-- cleans and reshapes them with plain SQL.

-- ---------- Clean station IDs ----------
-- 68 stations appear under two IDs because some rows lost a trailing zero ('5980.1' vs
-- '5980.10'), and a few IDs carry a stray underscore ('5303.06_'). Without this fix those
-- stations look like two half-size stations (one with only arrivals, one with departures).
UPDATE raw_trips SET start_station_id =
    CASE WHEN start_station_id GLOB '*.[0-9]' THEN start_station_id || '0'
         ELSE rtrim(start_station_id, '_') END
WHERE start_station_id GLOB '*.[0-9]' OR start_station_id GLOB '*_';

UPDATE raw_trips SET end_station_id =
    CASE WHEN end_station_id GLOB '*.[0-9]' THEN end_station_id || '0'
         ELSE rtrim(end_station_id, '_') END
WHERE end_station_id GLOB '*.[0-9]' OR end_station_id GLOB '*_';

-- ---------- Dimension: stations ----------
-- A station can show up with slightly different coordinates (e-bikes are docked near,
-- not exactly at, the dock), so we average them, and keep the most common name per ID.
CREATE TABLE stations (
    station_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    lat         REAL,
    lng         REAL,
    kind        TEXT NOT NULL        -- 'NYC', 'NJ' (Jersey City / Hoboken), 'system' (repair shop, depot)
);

INSERT INTO stations (station_id, name, lat, lng, kind)
WITH ends AS (
    SELECT start_station_id AS station_id, start_station_name AS name,
           CAST(start_lat AS REAL) AS lat, CAST(start_lng AS REAL) AS lng
    FROM raw_trips WHERE start_station_id <> ''
    UNION ALL
    SELECT end_station_id, end_station_name, CAST(end_lat AS REAL), CAST(end_lng AS REAL)
    FROM raw_trips WHERE end_station_id <> ''
),
name_rank AS (
    SELECT station_id, name,
           ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY COUNT(*) DESC, name) AS rn
    FROM ends
    GROUP BY station_id, name
)
SELECT n.station_id, n.name, AVG(e.lat), AVG(e.lng),
       CASE WHEN n.station_id GLOB 'JC*' OR n.station_id GLOB 'HB*' THEN 'NJ'
            WHEN n.station_id GLOB '[0-9]*' THEN 'NYC'
            ELSE 'system' END
FROM name_rank n
JOIN ends e ON e.station_id = n.station_id
WHERE n.rn = 1
GROUP BY n.station_id, n.name;

-- ---------- Dimension: daily weather (NOAA GHCN-Daily, Central Park USW00094728) ----------
-- GHCN stores one row per (date, element) in tenths of a unit; pivot to one row per day
-- and convert to US units.
CREATE TABLE weather_daily (
    date        TEXT PRIMARY KEY,   -- YYYY-MM-DD
    tmax_f      REAL,
    tmin_f      REAL,
    precip_in   REAL,
    wind_mph    REAL
);

INSERT INTO weather_daily
SELECT substr(date, 1, 4) || '-' || substr(date, 5, 2) || '-' || substr(date, 7, 2),
       ROUND(MAX(CASE WHEN element = 'TMAX' THEN value END) / 10.0 * 9 / 5 + 32, 1),
       ROUND(MAX(CASE WHEN element = 'TMIN' THEN value END) / 10.0 * 9 / 5 + 32, 1),
       ROUND(MAX(CASE WHEN element = 'PRCP' THEN value END) / 254.0, 2),
       ROUND(MAX(CASE WHEN element = 'AWND' THEN value END) / 10.0 * 2.23694, 1)
FROM raw_weather
WHERE q_flag = ''                -- drop values that failed NOAA quality checks
GROUP BY date;

-- ---------- Fact: trips ----------
CREATE TABLE trips (
    ride_id           TEXT PRIMARY KEY,
    rideable_type     TEXT NOT NULL,      -- classic_bike / electric_bike
    member_casual     TEXT NOT NULL,      -- member = annual pass, casual = day pass / single ride
    started_at        TEXT NOT NULL,      -- local time, 'YYYY-MM-DD HH:MM:SS'
    ended_at          TEXT NOT NULL,
    start_date        TEXT NOT NULL,      -- denormalized for fast GROUP BY / joins to weather
    start_hour        INTEGER NOT NULL,
    duration_min      REAL NOT NULL,
    start_station_id  TEXT REFERENCES stations(station_id),
    end_station_id    TEXT REFERENCES stations(station_id),   -- NULL if the bike was not docked
    distance_km       REAL                -- straight-line start->end distance, NULL if no end point
);

-- Keep every trip, including suspicious ones; 01_data_quality.sql reports them and the
-- analysis queries filter with the view below.
INSERT INTO trips
SELECT ride_id,
       rideable_type,
       member_casual,
       substr(started_at, 1, 19),
       substr(ended_at, 1, 19),
       substr(started_at, 1, 10),
       CAST(substr(started_at, 12, 2) AS INTEGER),
       ROUND((julianday(ended_at) - julianday(started_at)) * 1440, 2),
       NULLIF(start_station_id, ''),
       NULLIF(end_station_id, ''),
       -- Only when both points are inside the NYC area: a few thousand e-bike trips with no
       -- start station carry placeholder coordinates thousands of km away.
       CASE WHEN CAST(start_lat AS REAL) BETWEEN 40.4 AND 41.0 AND CAST(start_lng AS REAL) BETWEEN -74.4 AND -73.6
             AND CAST(end_lat   AS REAL) BETWEEN 40.4 AND 41.0 AND CAST(end_lng   AS REAL) BETWEEN -74.4 AND -73.6
       THEN ROUND(
           -- haversine distance in km
           2 * 6371 * asin(sqrt(
               power(sin(radians(CAST(end_lat AS REAL) - CAST(start_lat AS REAL)) / 2), 2) +
               cos(radians(CAST(start_lat AS REAL))) * cos(radians(CAST(end_lat AS REAL))) *
               power(sin(radians(CAST(end_lng AS REAL) - CAST(start_lng AS REAL)) / 2), 2))), 3)
       END
FROM raw_trips;

CREATE INDEX ix_trips_date      ON trips(start_date);
CREATE INDEX ix_trips_start_st  ON trips(start_station_id);
CREATE INDEX ix_trips_end_st    ON trips(end_station_id);

-- Analysis view: trips that look like real customer rides in September.
-- Under 1 minute = false starts / re-docks; over 3 hours = mostly lost or mis-docked bikes;
-- trips to or from a 'system' station are bikes moving to and from the repair shop.
CREATE VIEW rides AS
SELECT t.* FROM trips t
WHERE t.duration_min BETWEEN 1 AND 180
  AND t.start_date BETWEEN '2026-09-01' AND '2026-09-30'
  AND NOT EXISTS (SELECT 1 FROM stations s
                  WHERE s.kind = 'system'
                    AND s.station_id IN (t.start_station_id, t.end_station_id));

DROP TABLE raw_trips;
DROP TABLE raw_weather;
