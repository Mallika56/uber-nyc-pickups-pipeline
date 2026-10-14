"""Run the whole pipeline: download, create schema, load, build marts, print a quality report.

Usage:
    python -m pipeline.run                 # everything, skipping files already loaded
    python -m pipeline.run --force         # reload every file
    python -m pipeline.run --skip-download # use whatever is already in data/raw
"""

import argparse
import logging
import time

from pipeline.config import RAW_DIR
from pipeline.db import apply_schema, build_marts, connect
from pipeline.download import download
from pipeline.load import load_all

log = logging.getLogger("pipeline")


def main() -> None:
    """Parse arguments and run each stage in order."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="reload files already loaded")
    parser.add_argument("--skip-download", action="store_true", help="don't fetch missing files")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started = time.perf_counter()

    if not args.skip_download:
        download(RAW_DIR)

    with connect() as conn:
        apply_schema(conn)
        results = load_all(conn, RAW_DIR, force=args.force)
        log.info("building marts")
        build_marts(conn)
        quality = conn.execute(
            "SELECT total_pickups, exact_duplicates, outside_nyc_bbox, first_pickup, last_pickup "
            "FROM marts.quality_summary"
        ).fetchone()

    print("\nLoad report")
    print(f"{'file':<26}{'read':>12}{'loaded':>12}{'rejected':>10}  status")
    for r in results:
        status = "skipped (unchanged)" if r.skipped else "loaded"
        print(f"{r.source_file:<26}{r.rows_read:>12,}{r.rows_loaded:>12,}{r.rows_rejected:>10,}  {status}")

    total, dupes, outside, first, last = quality
    print(f"\nPickups in database: {total:,} ({first:%Y-%m-%d} to {last:%Y-%m-%d})")
    print(f"Exact duplicate rows (kept, see README): {dupes:,} ({dupes / total:.1%})")
    print(f"Outside the five boroughs (kept, flagged): {outside:,} ({outside / total:.1%})")
    print(f"Finished in {time.perf_counter() - started:.0f}s")


if __name__ == "__main__":
    main()
