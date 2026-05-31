"""Black-box tests for the Route Service."""

from datetime import date, time, timedelta

import pytest

from srmss.models import Bus, Driver
from srmss.services.route_service import RouteError

TODAY = date.today()


def test_create_route(container):
    r = container.route_service.create_route(1, "Kurunegala", "Colombo", 94.0)
    assert r.route_id == 1
    assert r.name == "Kurunegala \u2192 Colombo"
    assert container.route_service.list_routes()[0].distance == 94.0


def test_create_route_rejects_zero_distance(container):
    with pytest.raises(RouteError):
        container.route_service.create_route(1, "A", "B", 0)


def test_create_route_rejects_missing_endpoint(container):
    with pytest.raises(RouteError):
        container.route_service.create_route(1, "A", "", 10)


def test_bus_available_when_free(container):
    container.route_service.create_route(1, "A", "B", 10)
    bus = Bus(1, "NW-1", 50)
    container.buses.add(bus)
    assert container.route_service.is_bus_available(bus, TODAY, time(9, 0), time(11, 0)) is True


def test_bus_unavailable_when_booked(container):
    route = container.route_service.create_route(1, "A", "B", 10)
    bus = Bus(1, "NW-1", 50)
    container.buses.add(bus)
    driver = Driver(1, "D", "L", "active", TODAY + timedelta(days=365))
    container.drivers.add(driver)
    container.schedule_service.create_schedule(route, bus, driver, TODAY, time(9, 0), time(11, 0))
    assert container.route_service.is_bus_available(bus, TODAY, time(10, 0), time(12, 0)) is False


def test_driver_unavailable_when_licence_expired(container):
    container.route_service.create_route(1, "A", "B", 10)
    driver = Driver(1, "D", "L", "active", TODAY - timedelta(days=1))  # expired
    container.drivers.add(driver)
    assert container.route_service.is_driver_available(driver, TODAY, time(9, 0), time(11, 0)) is False


def test_update_route_modifies_fields(container):
    container.route_service.create_route(1, "A", "B", 10)
    container.route_service.update_route(1, "A", "C", 25)
    r = container.route_service.list_routes()[0]
    assert r.end_point == "C" and r.distance == 25


def test_suitable_buses_filters_capacity_type_availability(container):
    from srmss.models import Bus
    container.route_service.create_route(1, "A", "B", 10)
    container.buses.add(Bus(1, "BIG", 60, "single-decker"))
    container.buses.add(Bus(2, "SMALL", 20, "mini"))
    res = container.route_service.suitable_buses(
        TODAY, time(9, 0), time(11, 0), min_capacity=40, service_type="single-decker")
    regs = [b.reg_no for b in res]
    assert "BIG" in regs and "SMALL" not in regs
