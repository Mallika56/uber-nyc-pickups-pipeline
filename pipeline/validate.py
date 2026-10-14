"""Row-level validation for one batch of raw pickups. Pure pandas, so it is testable without a database."""

import pandas as pd

from pipeline.config import BASES, LAT_RANGE, LON_RANGE, TIMESTAMP_FORMAT

RAW_COLUMNS = ["Date/Time", "Lat", "Lon", "Base"]


def validate_batch(raw: pd.DataFrame, month: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a raw batch into rows ready to load and rows rejected with a reason.

    Rules are checked in order and a row gets the first reason it fails:
    bad_timestamp, missing_coordinates, coordinates_out_of_range, unknown_base, wrong_month.

    Returns (clean, rejected). `clean` has columns pickup_at, lat, lon, base_code;
    `rejected` has line_number, raw_row and reason.
    """
    missing = [c for c in RAW_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"source file is missing columns: {missing}")

    pickup_at = pd.to_datetime(raw["Date/Time"], format=TIMESTAMP_FORMAT, errors="coerce")
    lat = pd.to_numeric(raw["Lat"], errors="coerce")
    lon = pd.to_numeric(raw["Lon"], errors="coerce")
    base = raw["Base"].str.strip()

    reason = pd.Series(pd.NA, index=raw.index, dtype="object")

    def flag(mask: pd.Series, label: str) -> None:
        reason.loc[mask & reason.isna()] = label

    flag(pickup_at.isna(), "bad_timestamp")
    flag(lat.isna() | lon.isna(), "missing_coordinates")
    flag(~lat.between(*LAT_RANGE) | ~lon.between(*LON_RANGE), "coordinates_out_of_range")
    flag(~base.isin(list(BASES)), "unknown_base")
    flag(pickup_at.dt.month != month, "wrong_month")

    ok = reason.isna()
    clean = pd.DataFrame(
        {
            "pickup_at": pickup_at[ok],
            "lat": lat[ok],
            "lon": lon[ok],
            "base_code": base[ok],
        }
    )
    bad = ~ok
    if not bad.any():
        return clean, pd.DataFrame(columns=["line_number", "raw_row", "reason"])
    rejected = pd.DataFrame(
        {
            # +2: one for the header line, one because file lines are 1-based.
            "line_number": raw.index[bad] + 2,
            # fillna first: pandas keeps missing values as NaN even after astype(str).
            "raw_row": raw.loc[bad, RAW_COLUMNS].fillna("").astype(str).agg(",".join, axis=1),
            "reason": reason[bad],
        }
    )
    return clean, rejected
