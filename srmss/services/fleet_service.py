"""
services/fleet_service.py — Fleet Service (Tier 2).

Covers the fleet-facing use cases: Manage Vehicles, Manage Drivers,
Monitor/Update Trip Status, Log Fuel Usage, Log Maintenance, plus the
fuel-efficiency and service-due calculations from the brief.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from srmss.data.repositories import (
    BusRepository, DriverRepository, FuelLogRepository,
    MaintenanceLogRepository, TripRepository,
)
from srmss.models import Bus, Driver, FuelLog, MaintenanceLog, Trip


class FleetError(Exception):
    pass


class FleetService:
    def __init__(self, buses: BusRepository, drivers: DriverRepository,
                 trips: TripRepository, fuel: FuelLogRepository,
                 maintenance: MaintenanceLogRepository):
        self.buses = buses
        self.drivers = drivers
        self.trips = trips
        self.fuel = fuel
        self.maintenance = maintenance

    # -- Manage Vehicles / Drivers ---------------------------------------
    def list_buses(self) -> List[Bus]:
        return self.buses.all()

    def list_drivers(self) -> List[Driver]:
        return self.drivers.all()

    # -- Trip Status ------------------------------------------------------
    def list_trips(self) -> List[Trip]:
        return self.trips.all()

    def update_trip_status(self, trip_id: int, status: str) -> Trip:
        trip = self.trips.get(trip_id)
        if trip is None:
            raise FleetError(f"No trip with id {trip_id}")
        trip.update_status(status)          # validates via the model
        self.trips.set_status(trip_id, trip.status)
        return trip

    # -- Log Fuel ---------------------------------------------------------
    def log_fuel(self, bus: Bus, log_date: date, quantity: float,
                 cost: float, odometer: int = 0) -> FuelLog:
        if quantity <= 0:
            raise FleetError("Fuel quantity must be greater than 0")
        if cost < 0:
            raise FleetError("Cost cannot be negative")
        log = FuelLog(self.fuel.next_id(), bus, log_date, quantity, cost, odometer)
        self.fuel.add(log)
        return log

    # -- Log Maintenance --------------------------------------------------
    def log_maintenance(self, bus: Bus, log_date: date,
                        type_: str, cost: float) -> MaintenanceLog:
        if not type_.strip():
            raise FleetError("Maintenance needs a type/description")
        if cost < 0:
            raise FleetError("Cost cannot be negative")
        log = MaintenanceLog(self.maintenance.next_id(), bus, log_date, type_, cost)
        self.maintenance.add(log)
        return log

    # -- Calculations -----------------------------------------------------
    def fuel_efficiency(self, bus_id: int) -> Optional[float]:
        """
        km per litre for a bus using the tank-to-tank method:
        distance = (last odometer - first), litres = sum of fills after the
        first. Returns None if there are fewer than two fuel logs.
        """
        logs = self.fuel.for_bus(bus_id)
        if len(logs) < 2:
            return None
        logs.sort(key=lambda f: f.odometer)
        distance = logs[-1].odometer - logs[0].odometer
        litres = sum(f.quantity for f in logs[1:])
        if litres <= 0:
            return None
        return round(distance / litres, 2)

    def total_maintenance_cost(self, bus_id: int) -> float:
        return round(sum(m.cost for m in self.maintenance.for_bus(bus_id)), 2)

    def total_fuel_cost(self, bus_id: int) -> float:
        return round(sum(f.cost for f in self.fuel.for_bus(bus_id)), 2)

    def is_service_due(self, bus_id: int, mileage_interval: int = 10_000) -> bool:
        """Due if km since the lowest recorded odometer reaches the interval."""
        logs = self.fuel.for_bus(bus_id)
        if len(logs) < 2:
            return False
        odos = [f.odometer for f in logs]
        return (max(odos) - min(odos)) >= mileage_interval
