"""Shared fixtures: a test database loaded from a small hand-built source file.

The fixture file (tests/fixtures/uber-raw-data-apr14.csv) has 14 rows:
  9 valid  - including one exact duplicate pair and one Long Island pickup outside the boroughs
  5 invalid - one per validation rule, in rule order (bad_timestamp ... wrong_month)
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pipeline.db import apply_schema, build_marts, connect
from pipeline.load import load_file

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://localhost/uber_nyc_test")
FIXTURE_FILE = Path(__file__).parent / "fixtures" / "uber-raw-data-apr14.csv"


@pytest.fixture(scope="session")
def db():
    """A freshly built test database with the fixture file loaded and marts built."""
    conn = connect(TEST_DATABASE_URL)
    conn.execute("DROP SCHEMA IF EXISTS core, marts, meta CASCADE")
    apply_schema(conn)
    load_file(conn, FIXTURE_FILE)
    build_marts(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def client(db):
    """An API client pointed at the test database."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", TEST_DATABASE_URL)
        from api.main import app

        with TestClient(app) as test_client:
            yield test_client
