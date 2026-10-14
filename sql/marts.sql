-- Aggregates the API reads. Rebuilt from core.pickups after every load, inside one
-- transaction, so the API never sees a half-built mart.

-- Pickups per day and base: drives the daily trend and the per-base totals.
DROP TABLE IF EXISTS marts.daily_pickups;
CREATE TABLE marts.daily_pickups AS
SELECT pickup_at::date AS pickup_date,
       base_code,
       count(*)::integer AS pickups
FROM core.pickups
GROUP BY 1, 2;
CREATE INDEX ON marts.daily_pickups (pickup_date);

-- Pickups by ISO weekday (1 = Monday) and hour of day, per base.
DROP TABLE IF EXISTS marts.weekday_hour;
CREATE TABLE marts.weekday_hour AS
SELECT extract(isodow FROM pickup_at)::integer AS iso_weekday,
       extract(hour FROM pickup_at)::integer   AS hour,
       base_code,
       count(*)::integer AS pickups
FROM core.pickups
GROUP BY 1, 2, 3;

-- How many calendar days of each weekday the data covers. The API divides by this to turn
-- totals into an average per day, so a weekday that appears 27 times isn't compared raw
-- against one that appears 26 times.
DROP TABLE IF EXISTS marts.weekday_days;
CREATE TABLE marts.weekday_days AS
SELECT extract(isodow FROM day)::integer AS iso_weekday,
       count(*)::integer AS days
FROM (SELECT DISTINCT pickup_at::date AS day FROM core.pickups) AS d
GROUP BY 1;

-- Pickup density on a grid of 0.005-degree cells (about 550 m by 420 m) by hour, inside the
-- five boroughs. Coordinates are cell centres.
DROP TABLE IF EXISTS marts.pickup_grid;
CREATE TABLE marts.pickup_grid AS
SELECT round((floor(lat / 0.005) * 0.005 + 0.0025)::numeric, 4)::double precision AS cell_lat,
       round((floor(lon / 0.005) * 0.005 + 0.0025)::numeric, 4)::double precision AS cell_lon,
       extract(hour FROM pickup_at)::integer AS hour,
       count(*)::integer AS pickups
FROM core.pickups
WHERE in_nyc_bbox
GROUP BY 1, 2, 3;
CREATE INDEX ON marts.pickup_grid (hour);

-- One row of data-quality facts, reported rather than "fixed".
-- Exact duplicates share the same minute, coordinates and base. Timestamps only have minute
-- resolution, so two riders picked up at the same corner in the same minute look identical;
-- they are counted here and kept.
DROP TABLE IF EXISTS marts.quality_summary;
CREATE TABLE marts.quality_summary AS
SELECT count(*)::integer                                        AS total_pickups,
       (count(*) - count(DISTINCT (pickup_at, lat, lon, base_code)))::integer AS exact_duplicates,
       count(*) FILTER (WHERE NOT in_nyc_bbox)::integer        AS outside_nyc_bbox,
       min(pickup_at)                                           AS first_pickup,
       max(pickup_at)                                           AS last_pickup
FROM core.pickups;
