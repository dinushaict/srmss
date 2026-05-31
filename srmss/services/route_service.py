"""
services/route_service.py — Route Service (Tier 2).

Maps to "Manage Routes", "Assign Bus to Route", "Assign Driver".
Availability checks reuse the Schedule Service so the conflict rule lives in
one place only.
"""

from __future__ import annotations

from datetime import date, time
from typing import List, Optional

from srmss.data.repositories import (
    BusRepository, DriverRepository, RouteRepository, ScheduleRepository,
)
from srmss.models import Bus, Driver, Route, Stop
from srmss.services.schedule_service import ScheduleService


class RouteError(Exception):
    pass


class RouteService:
    def __init__(self, routes: RouteRepository, buses: BusRepository,
                 drivers: DriverRepository, schedule_service: ScheduleService):
        self.routes = routes
        self.buses = buses
        self.drivers = drivers
        self.schedule_service = schedule_service

    # -- Manage Routes ----------------------------------------------------
    def create_route(self, route_id: int, start_point: str, end_point: str,
                     distance: float, stops: Optional[List[Stop]] = None) -> Route:
        if not start_point or not end_point:
            raise RouteError("A route needs both a start and an end point")
        if distance <= 0:
            raise RouteError("Distance must be greater than 0")
        route = Route(route_id, start_point, end_point, distance, stops)
        self.routes.add(route)
        return route

    def list_routes(self) -> List[Route]:
        return self.routes.all()

    # -- Modify Route -----------------------------------------------------
    def update_route(self, route_id: int, start_point: str, end_point: str,
                     distance: float) -> Route:
        route = self.routes.get(route_id)
        if route is None:
            raise RouteError(f"No route with id {route_id}")
        if not start_point or not end_point:
            raise RouteError("A route needs both a start and an end point")
        if distance <= 0:
            raise RouteError("Distance must be greater than 0")
        route.start_point, route.end_point, route.distance = start_point, end_point, distance
        self.routes.update(route)
        return route

    # -- Suitable buses: capacity + service type + availability -----------
    def suitable_buses(self, sched_date: date, departure: time, arrival: time,
                       min_capacity: int = 0, service_type: str = "") -> List[Bus]:
        """
        Buses that match the brief's assignment criteria: enough capacity,
        the right service type (if given), AND free in the time window.
        """
        result = []
        for bus in self.buses.all():
            if bus.capacity < min_capacity:
                continue
            if service_type and bus.type != service_type:
                continue
            if self.schedule_service.is_bus_free(bus, sched_date, departure, arrival):
                result.append(bus)
        return result

    # -- Assign Bus to Route (availability-checked) -----------------------
    def is_bus_available(self, bus: Bus, sched_date: date,
                         departure: time, arrival: time) -> bool:
        return self.schedule_service.is_bus_free(bus, sched_date, departure, arrival)

    # -- Assign Driver (availability + licence) ---------------------------
    def is_driver_available(self, driver: Driver, sched_date: date,
                            departure: time, arrival: time) -> bool:
        if not driver.license_valid(sched_date):
            return False
        return self.schedule_service.is_driver_free(driver, sched_date, departure, arrival)
