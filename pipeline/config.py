"""Settings shared by the pipeline and the API: where the data lives and what valid data looks like."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = Path(os.environ.get("RAW_DIR", ROOT / "data" / "raw"))
SQL_DIR = ROOT / "sql"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/uber_nyc")

SOURCE_URL = (
    "https://raw.githubusercontent.com/fivethirtyeight/uber-tlc-foil-response/"
    "master/uber-trip-data/{name}"
)

# The six monthly files, keyed by the month abbreviation used in each file name.
MONTHS = {"apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9}
SOURCE_FILES = [f"uber-raw-data-{abbr}14.csv" for abbr in MONTHS]

# TLC base codes for Uber, as listed in the FiveThirtyEight dataset README.
BASES = {
    "B02512": "Unter",
    "B02598": "Hinter",
    "B02617": "Weiter",
    "B02682": "Schmecken",
    "B02764": "Danach-NY",
    "B02765": "Grun",
    "B02835": "Dreist",
    "B02836": "Drinnen",
}

# Sanity bounds for the wider New York region. A coordinate outside these is corrupt, not a
# real pickup, so the row is rejected. Pickups that are inside these bounds but outside the
# five boroughs (New Jersey, Long Island) are kept and flagged in the database instead.
LAT_RANGE = (39.0, 42.5)
LON_RANGE = (-75.5, -71.5)

TIMESTAMP_FORMAT = "%m/%d/%Y %H:%M:%S"
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100000"))


def file_month(file_name: str) -> int:
    """Return the calendar month a source file covers, from its name (uber-raw-data-apr14.csv -> 4)."""
    abbr = Path(file_name).name.removeprefix("uber-raw-data-")[:3]
    if abbr not in MONTHS:
        raise ValueError(f"not a recognised source file name: {file_name}")
    return MONTHS[abbr]
