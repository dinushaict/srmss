"""
models.py — SRMSS domain model.

These classes map directly to the Class Diagram. Attribute names follow the
diagram; method names use Python's snake_case convention, and each method's
docstring states the UML operation it implements (e.g. checkConflict ->
check_conflict). See the mapping table in README.md.

Inheritance (from the class diagram + design notes):

    User (abstract)
      ├── Administrator
      ├── Supervisor
      └── Clerk            (Depot Clerk)

Driver is a SEPARATE domain entity (it does NOT inherit from User).
"""

from __future__ import annotations

import hashlib
import os
import secrets
from abc import ABC, abstractmethod
from datetime import date, datetime, time
from typing import List, Optional


# ==========================================================================
# Users  (abstract User -> Administrator / Supervisor / Clerk)
# ==========================================================================
class User(ABC):
    """
    Abstract base class for accounts that can log in.

    Class diagram attributes: userId, username, password, role.
    Here `password` holds a salted hash (never plain text); the salt is stored
    alongside it. Methods login()/logout() from the diagram are implemented as
    login()/logout() below (logout state is managed by AuthService).
    """

    def __init__(self, user_id: int, username: str, password: str = "",
                 salt: str = "", role: str = ""):
        self.user_id = user_id          # userId
        self.username = username        # username
        self.password = password        # password (stored as a hash)
        self.salt = salt
        self.role = role or self.default_role()

    @abstractmethod
    def default_role(self) -> str:
        """Concrete user types declare their role string."""
        raise NotImplementedError

    # -- UML: login(): boolean --------------------------------------------
    def login(self, candidate: str) -> bool:
        """Return True if the candidate password matches the stored hash."""
        if not self.password or not self.salt:
            return False
        return secrets.compare_digest(
            hash_password(candidate, self.salt), self.password
        )

    # -- UML: logout(): void ----------------------------------------------
    def logout(self) -> None:
        """Model-level no-op; AuthService clears the session token."""
        return None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.user_id}, username={self.username!r})"


class Administrator(User):
    def default_role(self) -> str:
        return "Administrator"


class Supervisor(User):
    def default_role(self) -> str:
        return "Supervisor"


class Clerk(User):
    """Depot Clerk — handles daily assignments, fuel and maintenance logs."""
    def default_role(self) -> str:
        return "Clerk"


# Helper used by both models and the auth service.
def hash_password(plain: str, salt: str) -> str:
    """Return a hex pbkdf2-HMAC-SHA256 hash of `plain` using `salt`."""
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"),
                             bytes.fromhex(salt), 100_000)
    return dk.hex()


def make_salt() -> str:
    return os.urandom(16).hex()


# ==========================================================================
# Driver  (standalone entity, per the class diagram)
# ==========================================================================
class Driver:
    """Class diagram: driverId, name, licenseNo, status."""

    def __init__(self, driver_id: int, name: str, license_no: str,
                 status: str = "active", license_expiry: Optional[date] = None):
        self.driver_id = driver_id        # driverId
        self.name = name                  # name
        self.license_no = license_no      # licenseNo
        self.status = status              # status (active / on_leave / ...)
        # license_expiry supports the brief's "license validity" requirement
        self.license_expiry = license_expiry

    # -- UML: getDetails(): Driver ----------------------------------------
    def get_details(self) -> "Driver":
        return self

    # -- UML: updateInfo(): void ------------------------------------------
    def update_info(self, name: Optional[str] = None,
                    status: Optional[str] = None) -> None:
        if name is not None:
            self.name = name
        if status is not None:
            self.status = status

    def license_valid(self, on_date: Optional[date] = None) -> bool:
        """True if the licence has not expired (used before scheduling)."""
        if self.license_expiry is None:
            return True
        return self.license_expiry >= (on_date or date.today())

    def __repr__(self) -> str:
        return f"Driver(id={self.driver_id}, name={self.name!r})"


# ==========================================================================
# Bus
# ==========================================================================
class Bus:
    """Class diagram: regNo, capacity, type, status."""

    def __init__(self, bus_id: int, reg_no: str, capacity: int,
                 type_: str = "single-decker", status: str = "available"):
        self.bus_id = bus_id        # surrogate id (regNo is the business key)
        self.reg_no = reg_no        # regNo
        self.capacity = capacity    # capacity
        self.type = type_           # type
        self.status = status        # status (available / in_service / maintenance)

    # -- UML: getDetails(): Bus -------------------------------------------
    def get_details(self) -> "Bus":
        return self

    # -- UML: updateStatus(): void ----------------------------------------
    def update_status(self, status: str) -> None:
        self.status = status

    def __repr__(self) -> str:
        return f"Bus(id={self.bus_id}, reg={self.reg_no!r})"


# ==========================================================================
# Stop + Route  (Route owns Stops — composition)
# ==========================================================================
class Stop:
    def __init__(self, stop_id: int, name: str, sequence: int = 0):
        self.stop_id = stop_id
        self.name = name
        self.sequence = sequence

    def __repr__(self) -> str:
        return f"Stop(id={self.stop_id}, name={self.name!r})"


class Route:
    """Class diagram: routeId, startPoint, endPoint, distance (+ owns Stops)."""

    def __init__(self, route_id: int, start_point: str, end_point: str,
                 distance: float, stops: Optional[List[Stop]] = None):
        self.route_id = route_id          # routeId
        self.start_point = start_point    # startPoint
        self.end_point = end_point        # endPoint
        self.distance = distance          # distance (km)
        self.stops: List[Stop] = list(stops) if stops else []

    # -- UML: addStop(): void ---------------------------------------------
    def add_stop(self, stop: Stop) -> None:
        self.stops.append(stop)
        self.stops.sort(key=lambda s: s.sequence)

    # -- UML: getMapData(): Map -------------------------------------------
    def get_map_data(self) -> dict:
        """
        Route mapping via an online map service (brief requirement). Builds a
        Google Maps directions URL through start -> stops -> end. No API key is
        required for a directions link, so it works from any browser.
        """
        waypoints = [self.start_point] + [s.name for s in self.stops] + [self.end_point]
        query = "/".join(p.replace(" ", "+") for p in waypoints)
        return {
            "start": self.start_point,
            "end": self.end_point,
            "distance_km": self.distance,
            "stops": [s.name for s in self.stops],
            "google_maps_url": f"https://www.google.com/maps/dir/{query}",
        }

    @property
    def map_url(self) -> str:
        return self.get_map_data()["google_maps_url"]

    @property
    def name(self) -> str:
        return f"{self.start_point} \u2192 {self.end_point}"

    def __repr__(self) -> str:
        return f"Route(id={self.route_id}, {self.start_point}->{self.end_point})"


# ==========================================================================
# Schedule  (central entity: connects Route + Bus + Driver)
# ==========================================================================
class Schedule:
    """
    Class diagram: scheduleId, date, departureTime, arrivalTime
    (+ references to Route, Bus, Driver). Method: checkConflict(): boolean.
    """

    def __init__(self, schedule_id: int, route: Route, bus: Bus, driver: Driver,
                 sched_date: date, departure_time: time, arrival_time: time):
        self.schedule_id = schedule_id
        self.route = route
        self.bus = bus
        self.driver = driver
        self.date = sched_date
        self.departure_time = departure_time
        self.arrival_time = arrival_time

    def _start(self) -> datetime:
        return datetime.combine(self.date, self.departure_time)

    def _end(self) -> datetime:
        return datetime.combine(self.date, self.arrival_time)

    # -- UML: checkConflict(): boolean ------------------------------------
    def check_conflict(self, others: List["Schedule"]) -> bool:
        """
        True if this schedule clashes with any in `others`.
        Rule: overlap in time AND shares the same bus OR the same driver.
        Back-to-back times (one ends exactly when the next starts) do NOT clash.
        """
        for other in others:
            if other is self or other.schedule_id == self.schedule_id:
                continue
            same_bus = self.bus is not None and other.bus is not None \
                and self.bus.bus_id == other.bus.bus_id
            same_driver = self.driver is not None and other.driver is not None \
                and self.driver.driver_id == other.driver.driver_id
            if not (same_bus or same_driver):
                continue
            if self._start() < other._end() and other._start() < self._end():
                return True
        return False

    def __repr__(self) -> str:
        return (f"Schedule(id={self.schedule_id}, {self.date} "
                f"{self.departure_time}-{self.arrival_time})")


# ==========================================================================
# Trip  (a real journey produced from a Schedule)
# ==========================================================================
class Trip:
    """
    Class diagram: tripId, status, actualDeparture, actualArrival.
    Status values: planned / on-time / delayed / completed.
    """

    VALID_STATUSES = {"planned", "on-time", "delayed", "completed"}

    def __init__(self, trip_id: int, schedule: Schedule, status: str = "planned",
                 actual_departure: Optional[time] = None,
                 actual_arrival: Optional[time] = None):
        self.trip_id = trip_id
        self.schedule = schedule
        self.status = status
        self.actual_departure = actual_departure
        self.actual_arrival = actual_arrival

    # -- UML: updateStatus(): void ----------------------------------------
    def update_status(self, status: str) -> None:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid trip status: {status}")
        self.status = status

    # -- UML: complete(): void --------------------------------------------
    def complete(self, actual_arrival: Optional[time] = None) -> None:
        self.status = "completed"
        if actual_arrival is not None:
            self.actual_arrival = actual_arrival

    def __repr__(self) -> str:
        return f"Trip(id={self.trip_id}, status={self.status!r})"


# ==========================================================================
# Fuel & Maintenance logs
# ==========================================================================
class FuelLog:
    """Class diagram: logId, date, quantity, cost (+ which Bus)."""

    def __init__(self, log_id: int, bus: Bus, log_date: date,
                 quantity: float, cost: float, odometer: int = 0):
        self.log_id = log_id
        self.bus = bus
        self.date = log_date
        self.quantity = quantity     # litres
        self.cost = cost
        self.odometer = odometer     # supports efficiency calc

    # -- UML: record(): void ----------------------------------------------
    def record(self) -> "FuelLog":
        return self

    def __repr__(self) -> str:
        return f"FuelLog(id={self.log_id}, qty={self.quantity})"


class MaintenanceLog:
    """Class diagram: logId, date, type, cost (+ which Bus)."""

    def __init__(self, log_id: int, bus: Bus, log_date: date,
                 type_: str, cost: float):
        self.log_id = log_id
        self.bus = bus
        self.date = log_date
        self.type = type_            # e.g. "routine" / "corrective" / description
        self.cost = cost

    # -- UML: record(): void ----------------------------------------------
    def record(self) -> "MaintenanceLog":
        return self

    def __repr__(self) -> str:
        return f"MaintenanceLog(id={self.log_id}, type={self.type!r})"


# ==========================================================================
# Report
# ==========================================================================
class Report:
    """Class diagram: reportId, type, dateRange, generatedAt."""

    def __init__(self, report_id: int, type_: str, date_range: str = "",
                 rows: Optional[List[dict]] = None):
        self.report_id = report_id
        self.type = type_
        self.date_range = date_range
        self.generated_at = datetime.now()
        self.rows: List[dict] = list(rows) if rows else []

    def __repr__(self) -> str:
        return f"Report(id={self.report_id}, type={self.type!r})"
