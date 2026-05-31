"""
webapp/app.py — Tier 1 (Presentation).

A Flask app over the SRMSS services. It holds no business rules: every route
calls a Tier-2 service and renders the result. Data lives in an in-memory
SQLite database seeded at start-up (resets when the server restarts).

Run from the project root:   python run.py
Then open http://127.0.0.1:5000  (demo logins are shown on the sign-in page).
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, time
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import (
    Flask, flash, redirect, render_template, request, send_file, session, url_for
)

from srmss.container import build_container, seed_demo
from srmss.models import Stop
from srmss.services.auth_service import AuthError
from srmss.services.route_service import RouteError
from srmss.services.schedule_service import ScheduleError
from srmss.services.fleet_service import FleetError

app = Flask(__name__)
app.secret_key = "srmss-coursework-demo-key"

# Build + seed the in-memory system once at start-up.
C = build_container(":memory:")
seed_demo(C)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = session.get("token")
        if not token or C.auth.current_user(token) is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_username():
    return session.get("username")


@app.route("/")
def index():
    if session.get("token") and C.auth.current_user(session["token"]):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        try:
            token = C.auth.login(request.form.get("username", ""),
                                 request.form.get("password", ""))
            session["token"] = token
            session["username"] = request.form.get("username", "")
            return redirect(url_for("dashboard"))
        except AuthError:
            error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/dashboard")
@login_required
def dashboard():
    buses = C.fleet.list_buses()
    fleet_rows = []
    for b in buses:
        eff = C.fleet.fuel_efficiency(b.bus_id)
        fleet_rows.append({
            "reg_no": b.reg_no, "type": b.type, "status": b.status,
            "fuel_cost": C.fleet.total_fuel_cost(b.bus_id),
            "maint_cost": C.fleet.total_maintenance_cost(b.bus_id),
            "efficiency": eff if eff is not None else "n/a",
            "service_due": C.fleet.is_service_due(b.bus_id),
        })
    return render_template(
        "dashboard.html",
        username=current_username(),
        routes=C.route_service.list_routes(),
        drivers=C.fleet.list_drivers(),
        trips=C.fleet.list_trips(),
        fleet_rows=fleet_rows,
        trip_summary=C.reporting.trip_summary(),
        counts={"routes": len(C.route_service.list_routes()),
                "buses": len(buses),
                "drivers": len(C.fleet.list_drivers())},
        utilisation=C.reporting.vehicle_utilisation(),
        trip_statuses=["planned", "on-time", "delayed", "completed"],
    )


@app.route("/trips/<int:trip_id>/status", methods=["POST"])
@login_required
def update_trip(trip_id):
    try:
        C.fleet.update_trip_status(trip_id, request.form.get("status", ""))
        flash("Trip status updated.", "ok")
    except (FleetError, ValueError) as e:
        flash(str(e), "err")
    return redirect(url_for("dashboard"))


@app.route("/schedules", methods=["GET", "POST"])
@login_required
def schedules():
    if request.method == "POST":
        try:
            route = C.routes.get(int(request.form["route_id"]))
            bus = C.buses.get(int(request.form["bus_id"]))
            driver = C.drivers.get(int(request.form["driver_id"]))
            dep_h, dep_m = map(int, request.form["departure"].split(":"))
            arr_h, arr_m = map(int, request.form["arrival"].split(":"))
            frequency = request.form.get("frequency", "once")
            occurrences = int(request.form.get("occurrences", "1") or "1")
            if frequency == "once":
                C.schedule_service.create_schedule(
                    route, bus, driver, date.fromisoformat(request.form["date"]),
                    time(dep_h, dep_m), time(arr_h, arr_m))
                flash("Schedule created.", "ok")
            else:
                made = C.schedule_service.create_recurring(
                    route, bus, driver, date.fromisoformat(request.form["date"]),
                    time(dep_h, dep_m), time(arr_h, arr_m), frequency, occurrences)
                flash(f"Created {len(made)} schedule(s) ({frequency}).", "ok")
        except ScheduleError as e:
            flash(str(e), "err")
        except Exception:
            flash("Please fill in all fields correctly.", "err")
        return redirect(url_for("schedules"))

    return render_template(
        "schedules.html",
        username=current_username(),
        schedules=C.schedule_service.list_schedules(),
        routes=C.route_service.list_routes(),
        buses=C.fleet.list_buses(),
        drivers=C.fleet.list_drivers(),
        today=date.today().isoformat(),
    )


@app.route("/routes", methods=["GET", "POST"])
@login_required
def routes():
    """Route Planning UI — Manage Routes (create / modify / list + map link)."""
    if request.method == "POST":
        action = request.form.get("action", "create")
        try:
            if action == "edit":
                C.route_service.update_route(
                    int(request.form["route_id"]),
                    request.form["start_point"], request.form["end_point"],
                    float(request.form["distance"]))
                flash("Route updated.", "ok")
            else:
                stop_names = [s.strip() for s in request.form.get("stops", "").split(",") if s.strip()]
                stops = []
                for i, name in enumerate(stop_names, start=1):
                    stops.append(Stop(C.routes.next_stop_id() + i - 1, name, i))
                C.route_service.create_route(
                    C.routes.next_id(),
                    request.form["start_point"], request.form["end_point"],
                    float(request.form["distance"]), stops)
                flash("Route created.", "ok")
        except RouteError as e:
            flash(str(e), "err")
        except Exception:
            flash("Please fill in all fields correctly.", "err")
        return redirect(url_for("routes"))

    return render_template("routes.html", username=current_username(),
                           routes=C.route_service.list_routes())


@app.route("/fleet", methods=["GET", "POST"])
@login_required
def fleet():
    """Manage Vehicles + Log Fuel Usage + Log Maintenance."""
    if request.method == "POST":
        try:
            bus = C.buses.get(int(request.form["bus_id"]))
            log_date = date.fromisoformat(request.form["date"])
            if request.form["kind"] == "fuel":
                C.fleet.log_fuel(bus, log_date, float(request.form["quantity"]),
                                 float(request.form["cost"]), int(request.form["odometer"]))
                flash("Fuel log recorded.", "ok")
            else:
                C.fleet.log_maintenance(bus, log_date, request.form["type"],
                                        float(request.form["cost"]))
                flash("Maintenance log recorded.", "ok")
        except FleetError as e:
            flash(str(e), "err")
        except Exception:
            flash("Please fill in all fields correctly.", "err")
        return redirect(url_for("fleet"))

    buses = C.fleet.list_buses()
    bus_rows = [{
        "bus": b,
        "fuel_cost": C.fleet.total_fuel_cost(b.bus_id),
        "maint_cost": C.fleet.total_maintenance_cost(b.bus_id),
        "efficiency": C.fleet.fuel_efficiency(b.bus_id) or "n/a",
        "service_due": C.fleet.is_service_due(b.bus_id),
        "history": C.maintenance.for_bus(b.bus_id),
    } for b in buses]
    driver_rows = [{
        "driver": d,
        "hours": C.reporting.driver_working_hours(d.driver_id),
        "routes": C.reporting.driver_routes(d.driver_id),
    } for d in C.fleet.list_drivers()]
    return render_template("fleet.html", username=current_username(),
                           buses=buses, driver_rows=driver_rows,
                           bus_rows=bus_rows, today=date.today().isoformat())


@app.route("/reports")
@login_required
def reports():
    """Reports UI — on-screen fleet report + trip completion summary."""
    report = C.reporting.fleet_report()
    return render_template("reports.html", username=current_username(),
                           report=report, trip_summary=C.reporting.trip_summary(),
                           route_performance=C.reporting.route_performance(),
                           utilisation=C.reporting.vehicle_utilisation())


@app.route("/schedules/<int:schedule_id>/cancel", methods=["POST"])
@login_required
def cancel_schedule(schedule_id):
    try:
        C.schedule_service.cancel_schedule(schedule_id)
        flash("Schedule cancelled.", "ok")
    except ScheduleError as e:
        flash(str(e), "err")
    return redirect(url_for("schedules"))


@app.route("/report.pdf")
@login_required
def report_pdf():
    report = C.reporting.fleet_report()
    out = os.path.join(tempfile.gettempdir(), "srmss_fleet_report.pdf")
    C.reporting.export_pdf(report, out)
    return send_file(out, as_attachment=True, download_name="fleet_report.pdf")


@app.route("/logout")
def logout():
    token = session.pop("token", None)
    if token:
        C.auth.logout(token)
    session.clear()
    return redirect(url_for("login"))
