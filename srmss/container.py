"""
container.py — wires the three tiers together.

`build_container(path)` creates the database, all repositories (Tier 3) and all
services (Tier 2). `seed_demo(c)` fills a fresh database with realistic demo
data for the dashboard. Tests build their own in-memory container.
"""

from __future__ import annotations

from datetime import date, time, timedelta

from srmss.data.database import Database
from srmss.data.repositories import (
    BusRepository, DriverRepository, FuelLogRepository,
    MaintenanceLogRepository, RouteRepository, ScheduleRepository,
    TripRepository, UserRepository,
)
from srmss.models import (
    Administrator, Bus, Clerk, Driver, Route, Stop, Supervisor, Trip,
    hash_password, make_salt,
)
from srmss.services.auth_service import AuthService
from srmss.services.fleet_service import FleetService
from srmss.services.reporting_service import ReportingService
from srmss.services.route_service import RouteService
from srmss.services.schedule_service import ScheduleService


class Container:
    """Holds every repository and service. The composition root."""

    def __init__(self, db: Database):
        self.db = db
        # Tier 3 — repositories
        self.users = UserRepository(db)
        self.drivers = DriverRepository(db)
        self.buses = BusRepository(db)
        self.routes = RouteRepository(db)
        self.schedules = ScheduleRepository(db, self.routes, self.buses, self.drivers)
        self.trips = TripRepository(db, self.schedules)
        self.fuel = FuelLogRepository(db, self.buses)
        self.maintenance = MaintenanceLogRepository(db, self.buses)
        # Tier 2 — services
        self.auth = AuthService(self.users)
        self.schedule_service = ScheduleService(self.schedules)
        self.route_service = RouteService(
            self.routes, self.buses, self.drivers, self.schedule_service)
        self.fleet = FleetService(
            self.buses, self.drivers, self.trips, self.fuel, self.maintenance)
        self.reporting = ReportingService(self.fleet, self.schedule_service)


def build_container(path: str = ":memory:") -> Container:
    db = Database(path)
    db.init_schema()
    return Container(db)


def _user(repo, cls, uid, username, password):
    salt = make_salt()
    u = cls(uid, username, hash_password(password, salt), salt)
    repo.add(u)


def seed_demo(c: Container) -> None:
    """Insert a small, realistic depot dataset. Demo logins: see README."""
    # --- accounts (Administrator / Supervisor / Clerk) ---
    _user(c.users, Administrator, 1, "admin", "depot123")
    _user(c.users, Supervisor, 2, "supervisor", "super123")
    _user(c.users, Clerk, 3, "clerk", "clerk123")

    # --- drivers ---
    today = date.today()
    drivers = [
        Driver(1, "Nimal Perera", "B1234567", "active", today + timedelta(days=400)),
        Driver(2, "Kamala Silva", "B2345678", "active", today + timedelta(days=120)),
        Driver(3, "Sunil Fernando", "B3456789", "active", today - timedelta(days=10)),  # expired
    ]
    for d in drivers:
        c.drivers.add(d)

    # --- buses ---
    buses = [
        Bus(1, "NW-1234", 52, "single-decker", "available"),
        Bus(2, "NW-5678", 48, "single-decker", "in_service"),
        Bus(3, "NW-9012", 40, "mini", "maintenance"),
    ]
    for b in buses:
        c.buses.add(b)

    # --- routes (with stops) ---
    r1 = Route(1, "Kurunegala", "Colombo", 94.0, [
        Stop(1, "Polgahawela", 1), Stop(2, "Mirigama", 2), Stop(3, "Nittambuwa", 3)])
    r2 = Route(2, "Kurunegala", "Kandy", 42.0, [
        Stop(4, "Mawathagama", 1), Stop(5, "Galagedara", 2)])
    c.routes.add(r1)
    c.routes.add(r2)

    # --- schedules ---
    s1 = c.schedule_service.create_schedule(
        r1, buses[0], drivers[0], today, time(6, 0), time(8, 30))
    s2 = c.schedule_service.create_schedule(
        r2, buses[1], drivers[1], today, time(7, 0), time(8, 0))

    # --- trips (varied statuses for the dashboard) ---
    c.trips.add(Trip(1, s1, "completed", time(6, 2), time(8, 35)))
    c.trips.add(Trip(2, s2, "on-time", time(7, 1)))

    # --- fuel logs (two per bus where possible -> efficiency) ---
    c.fleet.log_fuel(buses[0], today - timedelta(days=10), 45, 9000, 12000)
    c.fleet.log_fuel(buses[0], today - timedelta(days=2), 50, 10000, 12600)
    c.fleet.log_fuel(buses[1], today - timedelta(days=9), 40, 8000, 30000)
    c.fleet.log_fuel(buses[1], today - timedelta(days=1), 42, 8400, 30520)
    c.fleet.log_fuel(buses[2], today - timedelta(days=1), 38, 7600, 50000)  # one log -> n/a

    # --- maintenance logs ---
    c.fleet.log_maintenance(buses[0], today - timedelta(days=20), "Brake pads", 18500)
    c.fleet.log_maintenance(buses[0], today - timedelta(days=5), "Oil & filter", 7200)
    c.fleet.log_maintenance(buses[2], today - timedelta(days=15), "Engine check", 26000)
