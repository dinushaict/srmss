"""
services/reporting_service.py — Reporting Service (Tier 2).

Maps to "Generate Reports" and Report.generate()/exportPDF(). Aggregates fleet
and trip data into a Report, and exports it to PDF. Aggregation is kept separate
from PDF rendering so the numbers can be tested without reading a PDF.
"""

from __future__ import annotations

from typing import List

from srmss.models import Report
from srmss.services.fleet_service import FleetService


class ReportingError(Exception):
    pass


class ReportingService:
    def __init__(self, fleet: FleetService, schedule_service=None):
        self.fleet = fleet
        self.schedule_service = schedule_service

    # -- vehicle utilisation rate (brief: dashboard summary stat) ----------
    def vehicle_utilisation(self) -> float:
        """Percentage of buses that have at least one schedule assigned."""
        buses = self.fleet.list_buses()
        if not buses or self.schedule_service is None:
            return 0.0
        assigned = {s.bus.bus_id for s in self.schedule_service.list_schedules()}
        used = len([b for b in buses if b.bus_id in assigned])
        return round(100 * used / len(buses), 1)

    # -- generate(): aggregate into a Report ------------------------------
    def fleet_report(self, report_id: int = 1) -> Report:
        rows: List[dict] = []
        for bus in self.fleet.list_buses():
            eff = self.fleet.fuel_efficiency(bus.bus_id)
            rows.append({
                "Bus": bus.reg_no,
                "Type": bus.type,
                "Fuel Cost": self.fleet.total_fuel_cost(bus.bus_id),
                "Maint. Cost": self.fleet.total_maintenance_cost(bus.bus_id),
                "Efficiency (km/L)": eff if eff is not None else "n/a",
                "Service Due": "YES" if self.fleet.is_service_due(bus.bus_id) else "no",
            })
        return Report(report_id, "Fleet Report", rows=rows)

    def trip_summary(self) -> dict:
        """Counts by trip status — feeds the dashboard statistics."""
        counts = {"planned": 0, "on-time": 0, "delayed": 0, "completed": 0}
        for trip in self.fleet.list_trips():
            counts[trip.status] = counts.get(trip.status, 0) + 1
        return counts

    # -- driver analytics (brief: working hours, assigned routes) ---------
    def _driver_schedules(self, driver_id: int):
        if self.schedule_service is None:
            return []
        return [s for s in self.schedule_service.list_schedules()
                if s.driver.driver_id == driver_id]

    def driver_working_hours(self, driver_id: int) -> float:
        """Total scheduled hours for a driver, summed across their schedules."""
        from datetime import datetime
        total = 0.0
        for s in self._driver_schedules(driver_id):
            start = datetime.combine(s.date, s.departure_time)
            end = datetime.combine(s.date, s.arrival_time)
            total += (end - start).total_seconds() / 3600.0
        return round(total, 1)

    def driver_routes(self, driver_id: int) -> list:
        """Distinct route names a driver is assigned to."""
        names = []
        for s in self._driver_schedules(driver_id):
            if s.route.name not in names:
                names.append(s.route.name)
        return names

    # -- route performance (brief: reporting & analytics) -----------------
    def route_performance(self) -> list:
        """Per-route trip counts and completion rate."""
        trips = self.fleet.list_trips()
        by_route = {}
        for t in trips:
            key = t.schedule.route.name
            entry = by_route.setdefault(key, {"Route": key, "Trips": 0, "Completed": 0})
            entry["Trips"] += 1
            if t.status == "completed":
                entry["Completed"] += 1
        rows = list(by_route.values())
        for r in rows:
            r["Completion %"] = round(100 * r["Completed"] / r["Trips"], 0) if r["Trips"] else 0
        return rows

    # -- exportPDF(): File ------------------------------------------------
    def export_pdf(self, report: Report, path: str) -> str:
        try:
            from fpdf import FPDF
        except ImportError as exc:  # pragma: no cover
            raise ReportingError("fpdf2 is not installed — run: pip install fpdf2") from exc

        def safe(value) -> str:
            text = str(value)
            for bad, good in {"\u2014": "-", "\u2013": "-", "\u2192": "->",
                              "\u2018": "'", "\u2019": "'"}.items():
                text = text.replace(bad, good)
            return text.encode("latin-1", "replace").decode("latin-1")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, safe(f"SRMSS {report.type}"))
        pdf.ln(12)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, safe(f"Generated: {report.generated_at:%Y-%m-%d %H:%M}"))
        pdf.ln(10)

        if not report.rows:
            pdf.cell(0, 8, "No data.")
            pdf.output(path)
            return path

        headers = list(report.rows[0].keys())
        width = pdf.epw / len(headers)
        pdf.set_font("Helvetica", "B", 9)
        for h in headers:
            pdf.cell(width, 8, safe(h), border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for row in report.rows:
            for h in headers:
                pdf.cell(width, 8, safe(row[h]), border=1)
            pdf.ln()

        pdf.output(path)
        return path
