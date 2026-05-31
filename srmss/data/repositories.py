"""
data/repositories.py — maps database rows to/from domain model objects.

Each repository hides the SQL for one entity so the service layer (Tier 2)
works with model objects, never raw rows. This is the boundary between the
Logic tier and the Data tier.
"""

from __future__ import annotations

from datetime import date, time
from typing import List, Optional

from srmss.data.database import Database
from srmss.models import (
    Administrator, Bus, Clerk, Driver, FuelLog, MaintenanceLog,
    Route, Schedule, Stop, Supervisor, Trip, User,
)

# ---- small (de)serialisation helpers ------------------------------------
def _d(s: Optional[str]) -> Optional[date]:
    return date.fromisoformat(s) if s else None


def _t(s: Optional[str]) -> Optional[time]:
    return time.fromisoformat(s) if s else None


_ROLE_CLASSES = {
    "Administrator": Administrator,
    "Supervisor": Supervisor,
    "Clerk": Clerk,
}


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, user: User) -> None:
        self.db.execute(
            "INSERT INTO users (user_id, username, password, salt, role) "
            "VALUES (?, ?, ?, ?, ?)",
            (user.user_id, user.username, user.password, user.salt, user.role),
        )

    def _row_to_user(self, row) -> User:
        cls = _ROLE_CLASSES.get(row["role"], Clerk)
        return cls(row["user_id"], row["username"], row["password"],
                   row["salt"], row["role"])

    def get_by_username(self, username: str) -> Optional[User]:
        row = self.db.query_one(
            "SELECT * FROM users WHERE username = ?", (username,))
        return self._row_to_user(row) if row else None


class DriverRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, d: Driver) -> None:
        self.db.execute(
            "INSERT INTO drivers (driver_id, name, license_no, status, license_expiry) "
            "VALUES (?, ?, ?, ?, ?)",
            (d.driver_id, d.name, d.license_no, d.status,
             d.license_expiry.isoformat() if d.license_expiry else None),
        )

    def _row(self, r) -> Driver:
        return Driver(r["driver_id"], r["name"], r["license_no"],
                      r["status"], _d(r["license_expiry"]))

    def get(self, driver_id: int) -> Optional[Driver]:
        r = self.db.query_one("SELECT * FROM drivers WHERE driver_id = ?", (driver_id,))
        return self._row(r) if r else None

    def all(self) -> List[Driver]:
        return [self._row(r) for r in self.db.query("SELECT * FROM drivers ORDER BY driver_id")]


class BusRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, b: Bus) -> None:
        self.db.execute(
            "INSERT INTO buses (bus_id, reg_no, capacity, type, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (b.bus_id, b.reg_no, b.capacity, b.type, b.status),
        )

    def update_status(self, bus_id: int, status: str) -> None:
        self.db.execute("UPDATE buses SET status = ? WHERE bus_id = ?", (status, bus_id))

    def _row(self, r) -> Bus:
        return Bus(r["bus_id"], r["reg_no"], r["capacity"], r["type"], r["status"])

    def get(self, bus_id: int) -> Optional[Bus]:
        r = self.db.query_one("SELECT * FROM buses WHERE bus_id = ?", (bus_id,))
        return self._row(r) if r else None

    def all(self) -> List[Bus]:
        return [self._row(r) for r in self.db.query("SELECT * FROM buses ORDER BY bus_id")]


class RouteRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, route: Route) -> None:
        self.db.execute(
            "INSERT INTO routes (route_id, start_point, end_point, distance) "
            "VALUES (?, ?, ?, ?)",
            (route.route_id, route.start_point, route.end_point, route.distance),
        )
        for stop in route.stops:
            self.db.execute(
                "INSERT INTO stops (stop_id, route_id, name, sequence) "
                "VALUES (?, ?, ?, ?)",
                (stop.stop_id, route.route_id, stop.name, stop.sequence),
            )

    def _stops(self, route_id: int) -> List[Stop]:
        rows = self.db.query(
            "SELECT * FROM stops WHERE route_id = ? ORDER BY sequence", (route_id,))
        return [Stop(r["stop_id"], r["name"], r["sequence"]) for r in rows]

    def _row(self, r) -> Route:
        return Route(r["route_id"], r["start_point"], r["end_point"],
                     r["distance"], self._stops(r["route_id"]))

    def get(self, route_id: int) -> Optional[Route]:
        r = self.db.query_one("SELECT * FROM routes WHERE route_id = ?", (route_id,))
        return self._row(r) if r else None

    def all(self) -> List[Route]:
        return [self._row(r) for r in self.db.query("SELECT * FROM routes ORDER BY route_id")]

    def next_id(self) -> int:
        r = self.db.query_one("SELECT COALESCE(MAX(route_id), 0) + 1 AS n FROM routes")
        return r["n"]

    def next_stop_id(self) -> int:
        r = self.db.query_one("SELECT COALESCE(MAX(stop_id), 0) + 1 AS n FROM stops")
        return r["n"]

    def update(self, route: Route) -> None:
        self.db.execute(
            "UPDATE routes SET start_point=?, end_point=?, distance=? WHERE route_id=?",
            (route.start_point, route.end_point, route.distance, route.route_id))


class ScheduleRepository:
    def __init__(self, db: Database, routes: RouteRepository,
                 buses: BusRepository, drivers: DriverRepository):
        self.db = db
        self.routes = routes
        self.buses = buses
        self.drivers = drivers

    def add(self, s: Schedule) -> None:
        self.db.execute(
            "INSERT INTO schedules (schedule_id, route_id, bus_id, driver_id, "
            "date, departure_time, arrival_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (s.schedule_id, s.route.route_id, s.bus.bus_id, s.driver.driver_id,
             s.date.isoformat(), s.departure_time.isoformat(),
             s.arrival_time.isoformat()),
        )

    def _row(self, r) -> Schedule:
        return Schedule(
            r["schedule_id"], self.routes.get(r["route_id"]),
            self.buses.get(r["bus_id"]), self.drivers.get(r["driver_id"]),
            _d(r["date"]), _t(r["departure_time"]), _t(r["arrival_time"]),
        )

    def get(self, schedule_id: int) -> Optional[Schedule]:
        r = self.db.query_one("SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,))
        return self._row(r) if r else None

    def all(self) -> List[Schedule]:
        return [self._row(r) for r in
                self.db.query("SELECT * FROM schedules ORDER BY date, departure_time")]

    def next_id(self) -> int:
        r = self.db.query_one("SELECT COALESCE(MAX(schedule_id), 0) + 1 AS n FROM schedules")
        return r["n"]

    def delete(self, schedule_id: int) -> None:
        self.db.execute("DELETE FROM trips WHERE schedule_id = ?", (schedule_id,))
        self.db.execute("DELETE FROM schedules WHERE schedule_id = ?", (schedule_id,))

    def update_times(self, schedule_id: int, sched_date, departure, arrival) -> None:
        self.db.execute(
            "UPDATE schedules SET date=?, departure_time=?, arrival_time=? WHERE schedule_id=?",
            (sched_date.isoformat(), departure.isoformat(), arrival.isoformat(), schedule_id))


class TripRepository:
    def __init__(self, db: Database, schedules: ScheduleRepository):
        self.db = db
        self.schedules = schedules

    def add(self, t: Trip) -> None:
        self.db.execute(
            "INSERT INTO trips (trip_id, schedule_id, status, actual_departure, "
            "actual_arrival) VALUES (?, ?, ?, ?, ?)",
            (t.trip_id, t.schedule.schedule_id, t.status,
             t.actual_departure.isoformat() if t.actual_departure else None,
             t.actual_arrival.isoformat() if t.actual_arrival else None),
        )

    def set_status(self, trip_id: int, status: str) -> None:
        self.db.execute("UPDATE trips SET status = ? WHERE trip_id = ?", (status, trip_id))

    def _row(self, r) -> Trip:
        return Trip(r["trip_id"], self.schedules.get(r["schedule_id"]),
                    r["status"], _t(r["actual_departure"]), _t(r["actual_arrival"]))

    def get(self, trip_id: int) -> Optional[Trip]:
        r = self.db.query_one("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
        return self._row(r) if r else None

    def all(self) -> List[Trip]:
        return [self._row(r) for r in self.db.query("SELECT * FROM trips ORDER BY trip_id")]


class FuelLogRepository:
    def __init__(self, db: Database, buses: BusRepository):
        self.db = db
        self.buses = buses

    def add(self, f: FuelLog) -> None:
        self.db.execute(
            "INSERT INTO fuel_logs (log_id, bus_id, date, quantity, cost, odometer) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (f.log_id, f.bus.bus_id, f.date.isoformat(), f.quantity, f.cost, f.odometer),
        )

    def _row(self, r) -> FuelLog:
        return FuelLog(r["log_id"], self.buses.get(r["bus_id"]), _d(r["date"]),
                       r["quantity"], r["cost"], r["odometer"])

    def all(self) -> List[FuelLog]:
        return [self._row(r) for r in self.db.query("SELECT * FROM fuel_logs ORDER BY date")]

    def for_bus(self, bus_id: int) -> List[FuelLog]:
        return [self._row(r) for r in self.db.query(
            "SELECT * FROM fuel_logs WHERE bus_id = ? ORDER BY odometer", (bus_id,))]

    def next_id(self) -> int:
        r = self.db.query_one("SELECT COALESCE(MAX(log_id), 0) + 1 AS n FROM fuel_logs")
        return r["n"]


class MaintenanceLogRepository:
    def __init__(self, db: Database, buses: BusRepository):
        self.db = db
        self.buses = buses

    def add(self, m: MaintenanceLog) -> None:
        self.db.execute(
            "INSERT INTO maintenance_logs (log_id, bus_id, date, type, cost) "
            "VALUES (?, ?, ?, ?, ?)",
            (m.log_id, m.bus.bus_id, m.date.isoformat(), m.type, m.cost),
        )

    def _row(self, r) -> MaintenanceLog:
        return MaintenanceLog(r["log_id"], self.buses.get(r["bus_id"]),
                              _d(r["date"]), r["type"], r["cost"])

    def all(self) -> List[MaintenanceLog]:
        return [self._row(r) for r in
                self.db.query("SELECT * FROM maintenance_logs ORDER BY date")]

    def for_bus(self, bus_id: int) -> List[MaintenanceLog]:
        return [self._row(r) for r in self.db.query(
            "SELECT * FROM maintenance_logs WHERE bus_id = ?", (bus_id,))]

    def next_id(self) -> int:
        r = self.db.query_one("SELECT COALESCE(MAX(log_id), 0) + 1 AS n FROM maintenance_logs")
        return r["n"]
