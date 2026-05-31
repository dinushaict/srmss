"""Black-box tests for the Fleet Service."""

from datetime import date

import pytest

from srmss.models import Bus
from srmss.services.fleet_service import FleetError

D = date(2025, 1, 1)


def _bus(container, bid=1):
    b = Bus(bid, f"NW-{bid}", 50)
    container.buses.add(b)
    return b


def test_log_fuel_validates_quantity(container):
    bus = _bus(container)
    with pytest.raises(FleetError):
        container.fleet.log_fuel(bus, D, 0, 100, 1000)


def test_log_maintenance_validates_cost(container):
    bus = _bus(container)
    with pytest.raises(FleetError):
        container.fleet.log_maintenance(bus, D, "Oil", -5)


def test_fuel_efficiency(container):
    bus = _bus(container)
    container.fleet.log_fuel(bus, D, 10, 20, 1000)   # baseline
    container.fleet.log_fuel(bus, D, 20, 40, 1200)
    container.fleet.log_fuel(bus, D, 20, 40, 1400)
    # distance 400, litres after first = 40 -> 10 km/L
    assert container.fleet.fuel_efficiency(bus.bus_id) == 10.0


def test_fuel_efficiency_none_with_one_log(container):
    bus = _bus(container)
    container.fleet.log_fuel(bus, D, 10, 20, 1000)
    assert container.fleet.fuel_efficiency(bus.bus_id) is None


def test_total_maintenance_cost(container):
    bus = _bus(container)
    container.fleet.log_maintenance(bus, D, "A", 100)
    container.fleet.log_maintenance(bus, D, "B", 250)
    assert container.fleet.total_maintenance_cost(bus.bus_id) == 350


def test_service_due_flag(container):
    bus = _bus(container)
    container.fleet.log_fuel(bus, D, 10, 20, 1000)
    container.fleet.log_fuel(bus, D, 10, 20, 12000)   # 11000 km span
    assert container.fleet.is_service_due(bus.bus_id) is True


def test_update_trip_status_validates(seeded):
    # trip 1 exists in the seed; invalid status should raise
    with pytest.raises(ValueError):
        seeded.fleet.update_trip_status(1, "flying")


def test_update_trip_status_persists(seeded):
    seeded.fleet.update_trip_status(1, "delayed")
    trip = seeded.trips.get(1)
    assert trip.status == "delayed"
