"""API tests: every endpoint, its filters, and its input validation."""

import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_summary_headline_numbers(client):
    body = client.get("/api/summary").json()
    assert body["total_pickups"] == 9
    assert (body["first_date"], body["last_date"]) == ("2014-04-01", "2014-04-30")
    assert body["days"] == 6
    assert body["busiest_day"] == {"date": "2014-04-01", "pickups": 3}
    assert body["peak_slot"] == {"iso_weekday": 2, "weekday": "Tue", "hour": 17, "avg_pickups": 2.0}
    assert body["monthly"] == [{"month": "2014-04-01", "pickups": 9}]
    assert body["growth_first_to_last_month_pct"] == 0.0
    assert body["quality"] == {"rejected_rows": 5, "exact_duplicates": 1, "outside_nyc_bbox": 1}


def test_summary_base_shares_add_up(client):
    bases = client.get("/api/summary").json()["bases"]
    assert sum(b["pickups"] for b in bases) == 9
    assert sum(b["share_pct"] for b in bases) == pytest.approx(100, abs=0.05)
    assert bases[0]["base_code"] == "B02617"


def test_daily_returns_every_day_in_order(client):
    body = client.get("/api/daily").json()
    assert [d["date"] for d in body] == [
        "2014-04-01", "2014-04-02", "2014-04-05", "2014-04-06", "2014-04-07", "2014-04-30",
    ]
    assert sum(d["pickups"] for d in body) == 9


def test_daily_filters_by_date_range_and_base(client):
    params = {"start": "2014-04-02", "end": "2014-04-30", "base": "B02617"}
    body = client.get("/api/daily", params=params).json()
    assert body == [{"date": "2014-04-02", "pickups": 2}, {"date": "2014-04-30", "pickups": 1}]


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2014-04-30", "end": "2014-04-01"},
        {"base": "B99999"},
        {"base": "uber"},
        {"start": "not-a-date"},
    ],
)
def test_daily_rejects_bad_input(client, params):
    assert client.get("/api/daily", params=params).status_code == 422


def test_hourly_averages_by_number_of_days(client):
    cells = {(c["iso_weekday"], c["hour"]): c["avg_pickups"] for c in client.get("/api/hourly").json()}
    assert cells[(2, 17)] == 2.0  # two pickups on the only Tuesday
    assert cells[(3, 8)] == 1.0   # two pickups across two Wednesdays
    assert cells[(3, 23)] == 0.5  # one pickup across two Wednesdays


def test_hourly_filters_by_base(client):
    body = client.get("/api/hourly", params={"base": "B02598"}).json()
    assert [(c["weekday"], c["hour"], c["avg_pickups"]) for c in body] == [("Tue", 17, 2.0)]


def test_hourly_rejects_unknown_base(client):
    assert client.get("/api/hourly", params={"base": "B99999"}).status_code == 422


def test_bases_for_a_month(client):
    body = client.get("/api/bases", params={"month": 4}).json()
    assert {b["base_code"]: b["pickups"] for b in body} == {
        "B02617": 3, "B02512": 2, "B02598": 2, "B02682": 1, "B02764": 1,
    }
    assert body[0]["base_name"] == "Weiter"


@pytest.mark.parametrize("month", [3, 10, 0])
def test_bases_rejects_months_outside_the_data(client, month):
    assert client.get("/api/bases", params={"month": month}).status_code == 422


def test_map_returns_grid_cells_for_an_hour_range(client):
    body = client.get("/api/map", params={"hour_from": 17, "hour_to": 17}).json()
    assert body == [{"lat": 40.7525, "lon": -73.9775, "pickups": 2}]


def test_map_min_pickups_filters_sparse_cells(client):
    assert client.get("/api/map", params={"min_pickups": 3}).json() == []


@pytest.mark.parametrize(
    "params",
    [{"hour_from": 20, "hour_to": 3}, {"hour_to": 24}, {"hour_from": -1}, {"min_pickups": 0}],
)
def test_map_rejects_bad_input(client, params):
    assert client.get("/api/map", params=params).status_code == 422
