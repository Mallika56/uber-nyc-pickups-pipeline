"""Integration tests for loading and the marts, against the test database."""

import pytest

from pipeline.load import load_all, load_file
from tests.conftest import FIXTURE_FILE


def count_pickups(db) -> int:
    return db.execute("SELECT count(*) FROM core.pickups").fetchone()[0]


def test_load_log_records_read_loaded_and_rejected(db):
    row = db.execute(
        "SELECT rows_read, rows_loaded, rows_rejected FROM meta.load_log WHERE source_file = %s",
        (FIXTURE_FILE.name,),
    ).fetchone()
    assert row == (14, 9, 5)
    assert count_pickups(db) == 9


def test_rejected_rows_keep_line_number_and_reason(db):
    rows = db.execute(
        "SELECT line_number, reason FROM meta.rejected_rows ORDER BY line_number"
    ).fetchall()
    assert rows == [
        (11, "bad_timestamp"),
        (12, "missing_coordinates"),
        (13, "coordinates_out_of_range"),
        (14, "unknown_base"),
        (15, "wrong_month"),
    ]


def test_unchanged_file_is_skipped_on_rerun(db):
    result = load_file(db, FIXTURE_FILE)
    assert result.skipped
    assert count_pickups(db) == 9


def test_forced_reload_replaces_rows_instead_of_duplicating(db):
    result = load_file(db, FIXTURE_FILE, force=True)
    assert not result.skipped
    assert (result.rows_loaded, result.rows_rejected) == (9, 5)
    assert count_pickups(db) == 9
    assert db.execute("SELECT count(*) FROM meta.rejected_rows").fetchone()[0] == 5


def test_small_batches_load_the_same_rows(db):
    result = load_file(db, FIXTURE_FILE, batch_size=4, force=True)
    assert (result.rows_read, result.rows_loaded, result.rows_rejected) == (14, 9, 5)
    assert count_pickups(db) == 9


def test_pickups_outside_the_boroughs_are_flagged_not_dropped(db):
    flagged = db.execute(
        "SELECT lat, lon FROM core.pickups WHERE NOT in_nyc_bbox"
    ).fetchall()
    assert flagged == [(40.75, -73.4)]


def test_quality_summary_counts_duplicates_and_outside_pickups(db):
    total, dupes, outside = db.execute(
        "SELECT total_pickups, exact_duplicates, outside_nyc_bbox FROM marts.quality_summary"
    ).fetchone()
    assert (total, dupes, outside) == (9, 1, 1)


def test_weekday_days_counts_calendar_days_per_weekday(db):
    rows = dict(db.execute("SELECT iso_weekday, days FROM marts.weekday_days").fetchall())
    # Apr 1 Tue, Apr 2 + Apr 30 Wed, Apr 5 Sat, Apr 6 Sun, Apr 7 Mon.
    assert rows == {1: 1, 2: 1, 3: 2, 6: 1, 7: 1}


def test_map_grid_excludes_pickups_outside_the_boroughs(db):
    total = db.execute("SELECT sum(pickups) FROM marts.pickup_grid").fetchone()[0]
    assert total == 8


def test_load_all_fails_clearly_when_files_are_missing(db, tmp_path):
    with pytest.raises(FileNotFoundError, match="pipeline.download"):
        load_all(db, tmp_path)
