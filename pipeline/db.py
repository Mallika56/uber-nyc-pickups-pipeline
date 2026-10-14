"""Database helpers for the pipeline: connecting, applying the schema, rebuilding the marts."""

import psycopg

from pipeline.config import BASES, DATABASE_URL, SQL_DIR


def connect(url: str | None = None) -> psycopg.Connection:
    """Open an autocommit connection; multi-statement work is wrapped in explicit transactions."""
    return psycopg.connect(url or DATABASE_URL, autocommit=True)


def apply_schema(conn: psycopg.Connection) -> None:
    """Create schemas, tables and indexes if missing, and upsert the base reference list."""
    with conn.transaction():
        conn.execute((SQL_DIR / "schema.sql").read_text())
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO core.bases (base_code, base_name) VALUES (%s, %s)
                ON CONFLICT (base_code) DO UPDATE SET base_name = EXCLUDED.base_name
                """,
                list(BASES.items()),
            )


def build_marts(conn: psycopg.Connection) -> None:
    """Rebuild every table in the marts schema from core.pickups in a single transaction."""
    with conn.transaction():
        conn.execute((SQL_DIR / "marts.sql").read_text())
