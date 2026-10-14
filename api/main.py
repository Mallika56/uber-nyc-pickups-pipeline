"""FastAPI service over the pickup marts. Also serves the built React dashboard when present.

Run locally:  uvicorn api.main:app --reload
"""

import datetime as dt
import os
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from api.schemas import BaseShare, DailyPoint, GridCell, Health, HourCell, Quality, Summary
from pipeline import config

WEEKDAYS = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
FIRST_MONTH, LAST_MONTH = min(config.MONTHS.values()), max(config.MONTHS.values())
DASHBOARD_DIR = config.ROOT / "dashboard" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one connection pool for the life of the process."""
    url = os.environ.get("DATABASE_URL", config.DATABASE_URL)
    app.state.pool = ConnectionPool(
        url, min_size=1, max_size=5, open=True, kwargs={"row_factory": dict_row, "autocommit": True}
    )
    yield
    app.state.pool.close()


app = FastAPI(
    title="Uber NYC Pickups Metrics API",
    description="Pickup demand by day, hour, weekday, base and location, April-September 2014.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_conn(request: Request) -> Iterator[psycopg.Connection]:
    """Borrow a pooled connection for one request."""
    with request.app.state.pool.connection() as conn:
        yield conn


Conn = Annotated[psycopg.Connection, Depends(get_conn)]
BaseCode = Annotated[
    str | None, Query(pattern=r"^B\d{5}$", description="TLC base code, e.g. B02617")
]


def check_base(base: str | None) -> None:
    """Reject a well-formed base code that isn't one of Uber's bases."""
    if base is not None and base not in config.BASES:
        raise HTTPException(status_code=422, detail=f"unknown base code {base}")


def hourly_rows(conn: psycopg.Connection, base: str | None) -> list[dict]:
    """Average pickups per day for every weekday-hour slot, optionally for one base."""
    return conn.execute(
        """
        SELECT w.iso_weekday, w.hour,
               round(sum(w.pickups)::numeric / d.days, 1)::float AS avg_pickups
        FROM marts.weekday_hour w
        JOIN marts.weekday_days d USING (iso_weekday)
        WHERE %(base)s::text IS NULL OR w.base_code = %(base)s
        GROUP BY w.iso_weekday, w.hour, d.days
        ORDER BY w.iso_weekday, w.hour
        """,
        {"base": base},
    ).fetchall()


def base_rows(conn: psycopg.Connection, month: int | None) -> list[dict]:
    """Pickups and percentage share per base, optionally within one month."""
    return conn.execute(
        """
        SELECT d.base_code, b.base_name, sum(d.pickups)::int AS pickups,
               round(sum(d.pickups) * 100.0 / sum(sum(d.pickups)) OVER (), 2)::float AS share_pct
        FROM marts.daily_pickups d
        JOIN core.bases b USING (base_code)
        WHERE %(month)s::int IS NULL OR extract(month FROM d.pickup_date) = %(month)s
        GROUP BY d.base_code, b.base_name
        ORDER BY pickups DESC
        """,
        {"month": month},
    ).fetchall()


@app.get("/health", response_model=Health)
def health(conn: Conn) -> Health:
    """Liveness check that also confirms the database answers."""
    conn.execute("SELECT 1")
    return Health(status="ok", database="ok")


@app.get("/api/summary", response_model=Summary)
def summary(conn: Conn) -> Summary:
    """Headline numbers: totals, busiest day, peak hour, monthly trend, base split, data quality."""
    quality = conn.execute("SELECT * FROM marts.quality_summary").fetchone()
    if quality is None or quality["total_pickups"] == 0:
        raise HTTPException(status_code=503, detail="no data loaded yet; run the pipeline")

    rejected = conn.execute(
        "SELECT coalesce(sum(rows_rejected), 0)::int AS n FROM meta.load_log"
    ).fetchone()["n"]
    days = conn.execute(
        "SELECT count(DISTINCT pickup_date)::int AS n FROM marts.daily_pickups"
    ).fetchone()["n"]
    busiest = conn.execute(
        """
        SELECT pickup_date AS date, sum(pickups)::int AS pickups
        FROM marts.daily_pickups GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 1
        """
    ).fetchone()
    monthly = conn.execute(
        """
        SELECT date_trunc('month', pickup_date)::date AS month, sum(pickups)::int AS pickups
        FROM marts.daily_pickups GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    peak = max(hourly_rows(conn, None), key=lambda r: r["avg_pickups"])

    first, last = monthly[0]["pickups"], monthly[-1]["pickups"]
    return Summary(
        total_pickups=quality["total_pickups"],
        first_date=quality["first_pickup"].date(),
        last_date=quality["last_pickup"].date(),
        days=days,
        busiest_day=DailyPoint(**busiest),
        peak_slot=HourCell(**peak, weekday=WEEKDAYS[peak["iso_weekday"]]),
        monthly=monthly,
        growth_first_to_last_month_pct=round((last - first) * 100 / first, 1),
        bases=[BaseShare(**r) for r in base_rows(conn, None)],
        quality=Quality(
            rejected_rows=rejected,
            exact_duplicates=quality["exact_duplicates"],
            outside_nyc_bbox=quality["outside_nyc_bbox"],
        ),
    )


@app.get("/api/daily", response_model=list[DailyPoint])
def daily(
    conn: Conn,
    start: dt.date | None = None,
    end: dt.date | None = None,
    base: BaseCode = None,
) -> list[DailyPoint]:
    """Pickups per day, optionally within [start, end] and for one base."""
    check_base(base)
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    rows = conn.execute(
        """
        SELECT pickup_date AS date, sum(pickups)::int AS pickups
        FROM marts.daily_pickups
        WHERE (%(start)s::date IS NULL OR pickup_date >= %(start)s)
          AND (%(end)s::date IS NULL OR pickup_date <= %(end)s)
          AND (%(base)s::text IS NULL OR base_code = %(base)s)
        GROUP BY 1 ORDER BY 1
        """,
        {"start": start, "end": end, "base": base},
    ).fetchall()
    return [DailyPoint(**r) for r in rows]


@app.get("/api/hourly", response_model=list[HourCell])
def hourly(conn: Conn, base: BaseCode = None) -> list[HourCell]:
    """Average pickups per day for each weekday and hour: the data behind the heatmap."""
    check_base(base)
    return [
        HourCell(**r, weekday=WEEKDAYS[r["iso_weekday"]]) for r in hourly_rows(conn, base)
    ]


@app.get("/api/bases", response_model=list[BaseShare])
def bases(
    conn: Conn,
    month: Annotated[int | None, Query(ge=FIRST_MONTH, le=LAST_MONTH)] = None,
) -> list[BaseShare]:
    """Pickups and share per dispatch base, for the whole period or one month (4-9)."""
    return [BaseShare(**r) for r in base_rows(conn, month)]


@app.get("/api/map", response_model=list[GridCell])
def pickup_map(
    conn: Conn,
    hour_from: Annotated[int, Query(ge=0, le=23)] = 0,
    hour_to: Annotated[int, Query(ge=0, le=23)] = 23,
    min_pickups: Annotated[int, Query(ge=1)] = 1,
) -> list[GridCell]:
    """Pickup counts per map grid cell inside the five boroughs, for an hour-of-day range."""
    if hour_from > hour_to:
        raise HTTPException(status_code=422, detail="hour_from must be <= hour_to")
    rows = conn.execute(
        """
        SELECT cell_lat AS lat, cell_lon AS lon, sum(pickups)::int AS pickups
        FROM marts.pickup_grid
        WHERE hour BETWEEN %(lo)s AND %(hi)s
        GROUP BY 1, 2
        HAVING sum(pickups) >= %(min)s
        """,
        {"lo": hour_from, "hi": hour_to, "min": min_pickups},
    ).fetchall()
    return [GridCell(**r) for r in rows]


# Mounted last so the API routes above take precedence over the static files.
if DASHBOARD_DIR.exists():
    app.mount("/", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")
