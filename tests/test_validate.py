"""Unit tests for row validation. No database needed."""

import pandas as pd
import pytest

from pipeline.config import file_month
from pipeline.validate import validate_batch

GOOD = {"Date/Time": "4/1/2014 0:11:00", "Lat": "40.769", "Lon": "-73.9549", "Base": "B02512"}


def batch(*overrides: dict) -> pd.DataFrame:
    """Build a raw batch where each row is the good row with some fields replaced."""
    return pd.DataFrame([{**GOOD, **o} for o in overrides], dtype=str)


def test_valid_row_is_parsed_into_typed_columns():
    clean, rejected = validate_batch(batch({}), month=4)
    assert rejected.empty
    row = clean.iloc[0]
    assert row["pickup_at"] == pd.Timestamp("2014-04-01 00:11:00")
    assert row["lat"] == pytest.approx(40.769)
    assert row["lon"] == pytest.approx(-73.9549)
    assert row["base_code"] == "B02512"


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"Date/Time": "not a date"}, "bad_timestamp"),
        ({"Date/Time": "2014-04-01 00:11"}, "bad_timestamp"),
        ({"Lat": None}, "missing_coordinates"),
        ({"Lon": "abc"}, "missing_coordinates"),
        ({"Lat": "0", "Lon": "0"}, "coordinates_out_of_range"),
        ({"Lat": "45.0"}, "coordinates_out_of_range"),
        ({"Base": "B99999"}, "unknown_base"),
        ({"Base": None}, "unknown_base"),
        ({"Date/Time": "5/1/2014 0:00:00"}, "wrong_month"),
    ],
)
def test_each_rule_rejects_with_its_reason(override, reason):
    clean, rejected = validate_batch(batch(override), month=4)
    assert clean.empty
    assert rejected["reason"].tolist() == [reason]


def test_first_failing_rule_wins():
    clean, rejected = validate_batch(batch({"Date/Time": "garbage", "Base": "B99999"}), month=4)
    assert rejected["reason"].tolist() == ["bad_timestamp"]


def test_base_code_whitespace_is_trimmed():
    clean, _ = validate_batch(batch({"Base": " B02512 "}), month=4)
    assert clean["base_code"].tolist() == ["B02512"]


def test_line_numbers_point_at_the_source_file_line():
    raw = batch({}, {"Base": "B99999"}, {})
    _, rejected = validate_batch(raw, month=4)
    # Row index 1 is the third line of the file: header on line 1, first data row on line 2.
    assert rejected["line_number"].tolist() == [3]


def test_mixed_batch_splits_cleanly():
    raw = batch({}, {"Lat": None}, {}, {"Date/Time": "5/2/2014 1:00:00"})
    clean, rejected = validate_batch(raw, month=4)
    assert len(clean) == 2
    assert sorted(rejected["reason"]) == ["missing_coordinates", "wrong_month"]


def test_missing_column_raises():
    with pytest.raises(ValueError, match="missing columns"):
        validate_batch(batch({}).drop(columns=["Base"]), month=4)


@pytest.mark.parametrize(
    ("name", "month"),
    [("uber-raw-data-apr14.csv", 4), ("uber-raw-data-sep14.csv", 9), ("data/raw/uber-raw-data-jul14.csv", 7)],
)
def test_file_month_reads_the_month_from_the_name(name, month):
    assert file_month(name) == month


def test_file_month_rejects_unknown_names():
    with pytest.raises(ValueError):
        file_month("uber-raw-data-dec14.csv")
