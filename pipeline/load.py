"""Load the monthly source files into core.pickups in validated batches."""

import hashlib
import io
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg

from pipeline.config import BATCH_SIZE, SOURCE_FILES, file_month
from pipeline.validate import validate_batch

log = logging.getLogger(__name__)

COPY_SQL = (
    "COPY core.pickups (pickup_at, lat, lon, base_code, source_file) "
    "FROM STDIN WITH (FORMAT csv)"
)


@dataclass
class LoadResult:
    """What happened to one source file."""

    source_file: str
    rows_read: int
    rows_loaded: int
    rows_rejected: int
    skipped: bool = False


def sha256_of(path: Path) -> str:
    """Checksum a file, so a re-run can tell an unchanged file from a corrected one."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_batch(cur: psycopg.Cursor, clean: pd.DataFrame, source_file: str) -> None:
    """Stream one validated batch into core.pickups with COPY, far faster than row INSERTs."""
    buf = io.StringIO()
    clean.assign(source_file=source_file).to_csv(
        buf, index=False, header=False, date_format="%Y-%m-%d %H:%M:%S"
    )
    with cur.copy(COPY_SQL) as copy:
        copy.write(buf.getvalue())


def load_file(
    conn: psycopg.Connection, path: Path, batch_size: int = BATCH_SIZE, force: bool = False
) -> LoadResult:
    """Load one source file, batch by batch, in a single transaction.

    Idempotent: a file already loaded with the same checksum is skipped. A changed file (or
    force=True) has its previous rows deleted and reloaded in the same transaction, so a failed
    reload leaves the earlier load intact instead of half-replaced.
    """
    name = path.name
    month = file_month(name)
    digest = sha256_of(path)

    previous = conn.execute(
        "SELECT sha256, rows_read, rows_loaded, rows_rejected FROM meta.load_log "
        "WHERE source_file = %s",
        (name,),
    ).fetchone()
    if previous and previous[0] == digest and not force:
        log.info("%s unchanged since last load, skipping", name)
        return LoadResult(name, previous[1], previous[2], previous[3], skipped=True)

    read = loaded = rejected = 0
    with conn.transaction(), conn.cursor() as cur:
        for table in ("core.pickups", "meta.rejected_rows", "meta.load_log"):
            cur.execute(f"DELETE FROM {table} WHERE source_file = %s", (name,))

        for raw in pd.read_csv(path, dtype=str, chunksize=batch_size):
            clean, bad = validate_batch(raw, month)
            if len(clean):
                copy_batch(cur, clean, name)
            if len(bad):
                cur.executemany(
                    "INSERT INTO meta.rejected_rows (source_file, line_number, raw_row, reason) "
                    "VALUES (%s, %s, %s, %s)",
                    [(name, int(r.line_number), r.raw_row, r.reason) for r in bad.itertuples()],
                )
            read += len(raw)
            loaded += len(clean)
            rejected += len(bad)
            log.info("%s: %s rows read so far", name, f"{read:,}")

        cur.execute(
            "INSERT INTO meta.load_log "
            "(source_file, sha256, rows_read, rows_loaded, rows_rejected) "
            "VALUES (%s, %s, %s, %s, %s)",
            (name, digest, read, loaded, rejected),
        )

    log.info("%s: loaded %s, rejected %s", name, f"{loaded:,}", f"{rejected:,}")
    return LoadResult(name, read, loaded, rejected)


def load_all(conn: psycopg.Connection, raw_dir: Path, force: bool = False) -> list[LoadResult]:
    """Load every expected source file from raw_dir, then refresh planner statistics."""
    missing = [name for name in SOURCE_FILES if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"missing source files in {raw_dir}: {missing}. Run `python -m pipeline.download`."
        )
    results = [load_file(conn, raw_dir / name, force=force) for name in SOURCE_FILES]
    conn.execute("ANALYZE core.pickups")
    return results
