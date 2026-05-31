"""Smoke tests for the Flask presentation tier."""

import pytest

pytest.importorskip("flask")

from webapp.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302


def test_login_and_dashboard(client):
    resp = client.post("/login", data={"username": "admin", "password": "depot123"})
    assert resp.status_code == 302
    dash = client.get("/dashboard")
    assert dash.status_code == 200
    assert b"Kurunegala Central Depot" in dash.data
    assert b"NW-1234" in dash.data


def test_bad_login(client):
    resp = client.post("/login", data={"username": "admin", "password": "nope"})
    assert b"Invalid username or password" in resp.data


def test_schedules_page_loads(client):
    client.post("/login", data={"username": "admin", "password": "depot123"})
    assert client.get("/schedules").status_code == 200


def test_report_pdf_downloads(client):
    client.post("/login", data={"username": "admin", "password": "depot123"})
    resp = client.get("/report.pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"


def test_routes_page_and_create(client):
    client.post("/login", data={"username": "admin", "password": "depot123"})
    assert client.get("/routes").status_code == 200
    resp = client.post("/routes", data={
        "start_point": "Kurunegala", "end_point": "Dambulla",
        "distance": "72", "stops": "Ibbagamuwa, Melsiripura"},
        follow_redirects=True)
    assert b"Route created" in resp.data


def test_fleet_page_and_log_fuel(client):
    client.post("/login", data={"username": "admin", "password": "depot123"})
    assert client.get("/fleet").status_code == 200
    resp = client.post("/fleet", data={
        "kind": "fuel", "bus_id": "1", "date": "2025-02-01",
        "quantity": "40", "cost": "9000", "odometer": "13000"},
        follow_redirects=True)
    assert b"Fuel log recorded" in resp.data


def test_reports_page_loads(client):
    client.post("/login", data={"username": "admin", "password": "depot123"})
    resp = client.get("/reports")
    assert resp.status_code == 200
    assert b"Fleet report" in resp.data
