"""Response models for the metrics API."""

import datetime as dt

from pydantic import BaseModel


class Health(BaseModel):
    """Service and database status."""

    status: str
    database: str


class DailyPoint(BaseModel):
    """Pickups on one calendar day."""

    date: dt.date
    pickups: int


class MonthPoint(BaseModel):
    """Pickups in one calendar month."""

    month: dt.date
    pickups: int


class HourCell(BaseModel):
    """Average pickups per day for one weekday-and-hour slot (iso_weekday 1 = Monday)."""

    iso_weekday: int
    weekday: str
    hour: int
    avg_pickups: float


class BaseShare(BaseModel):
    """One dispatch base's pickups and share of the total."""

    base_code: str
    base_name: str
    pickups: int
    share_pct: float


class GridCell(BaseModel):
    """Pickups in one map grid cell; lat/lon are the cell centre."""

    lat: float
    lon: float
    pickups: int


class Quality(BaseModel):
    """Data-quality facts reported by the pipeline."""

    rejected_rows: int
    exact_duplicates: int
    outside_nyc_bbox: int


class Summary(BaseModel):
    """Headline numbers for the dashboard's top row."""

    total_pickups: int
    first_date: dt.date
    last_date: dt.date
    days: int
    busiest_day: DailyPoint
    peak_slot: HourCell
    monthly: list[MonthPoint]
    growth_first_to_last_month_pct: float
    bases: list[BaseShare]
    quality: Quality
