"""Black-box tests for the Reporting Service."""


def test_fleet_report_has_row_per_bus(seeded):
    report = seeded.reporting.fleet_report()
    assert len(report.rows) == len(seeded.fleet.list_buses())
    assert report.rows[0]["Bus"] == "NW-1234"


def test_fleet_report_efficiency_na_for_single_log_bus(seeded):
    report = seeded.reporting.fleet_report()
    na_rows = [r for r in report.rows if r["Efficiency (km/L)"] == "n/a"]
    assert len(na_rows) >= 1   # NW-9012 has only one fuel log


def test_trip_summary_counts(seeded):
    counts = seeded.reporting.trip_summary()
    assert counts["completed"] == 1
    assert counts["on-time"] == 1


def test_export_pdf_writes_valid_file(seeded, tmp_path):
    report = seeded.reporting.fleet_report()
    out = tmp_path / "report.pdf"
    seeded.reporting.export_pdf(report, str(out))
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_vehicle_utilisation(seeded):
    # 2 of the 3 seeded buses have schedules -> ~66.7%
    util = seeded.reporting.vehicle_utilisation()
    assert 60.0 <= util <= 70.0


def test_driver_working_hours(seeded):
    # seeded driver 1 has a 06:00-08:30 schedule -> 2.5 h
    assert seeded.reporting.driver_working_hours(1) == 2.5


def test_driver_routes_lists_assigned(seeded):
    routes = seeded.reporting.driver_routes(1)
    assert any("Colombo" in r for r in routes)


def test_route_performance_has_rows(seeded):
    perf = seeded.reporting.route_performance()
    assert len(perf) >= 1
    assert "Completion %" in perf[0]
