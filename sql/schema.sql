-- Schema for the Uber NYC pickups pipeline. Safe to run repeatedly.
--   core  : cleaned, row-level pickups
--   marts : aggregates rebuilt after every load, read by the API
--   meta  : load bookkeeping (what was loaded, when, and what was rejected)

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE IF NOT EXISTS core.bases (
    base_code text PRIMARY KEY,
    base_name text NOT NULL
);

-- Timestamps are New York local time as published by the TLC. The whole April-September
-- range falls inside daylight saving time, so there are no ambiguous or skipped hours.
CREATE TABLE IF NOT EXISTS core.pickups (
    pickup_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pickup_at   timestamp        NOT NULL,
    lat         double precision NOT NULL,
    lon         double precision NOT NULL,
    base_code   text             NOT NULL REFERENCES core.bases (base_code),
    source_file text             NOT NULL,
    -- Rough bounding box of the five boroughs. Pickups outside it (New Jersey, Long Island,
    -- Westchester) are real trips, so they are flagged rather than dropped.
    in_nyc_bbox boolean GENERATED ALWAYS AS (
        lat BETWEEN 40.4774 AND 40.9176 AND lon BETWEEN -74.2591 AND -73.7004
    ) STORED
);

-- Most queries filter on time; per-base queries filter on base and then time.
CREATE INDEX IF NOT EXISTS pickups_pickup_at_idx ON core.pickups (pickup_at);
CREATE INDEX IF NOT EXISTS pickups_base_time_idx ON core.pickups (base_code, pickup_at);
CREATE INDEX IF NOT EXISTS pickups_source_file_idx ON core.pickups (source_file);

CREATE TABLE IF NOT EXISTS meta.load_log (
    source_file   text PRIMARY KEY,
    sha256        text        NOT NULL,
    rows_read     integer     NOT NULL,
    rows_loaded   integer     NOT NULL,
    rows_rejected integer     NOT NULL,
    loaded_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS meta.rejected_rows (
    source_file text    NOT NULL,
    line_number integer NOT NULL,
    raw_row     text    NOT NULL,
    reason      text    NOT NULL,
    PRIMARY KEY (source_file, line_number)
);
