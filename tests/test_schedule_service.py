"""Black-box tests for the Schedule Service — the core conflict logic."""

from datetime import date, time, timedelta

import pytest

from srmss.models import Bus, Driver, Route
from srmss.services.schedule_service import ScheduleError


def _setup(container):
    route = container.route_service.create_route(1, "A", "B", 50)
    bus = Bus(1, "NW-1", 50)
    container.buses.add(bus)
    driver = Driver(1, "Test Driver", "L1", "active",
                    date.today() + timedelta(days=365))
    container.drivers.add(driver)
    return route, bus, driver


TODAY = date.today()


def test_create_schedule_succeeds(container):
    route, bus, driver = _setup(container)
    s = container.schedule_service.create_schedule(
        route, bus, driver, TODAY, time(9, 0), time(11, 0))
    assert s.schedule_id is not None
    assert len(container.schedule_service.list_schedules()) == 1


def test_conflict_same_bus_overlapping_is_rejected(container):
    route, bus, driver = _setup(container)
    other = Driver(2, "D2", "L2", "active", TODAY + timedelta(days=365))
    container.drivers.add(other)
    container.schedule_service.create_schedule(route, bus, driver, TODAY, time(9, 0), time(11, 0))
    with pytest.raises(ScheduleError):       # same bus, overlapping time
        container.schedule_service.create_schedule(route, bus, other, TODAY, time(10, 0), time(12, 0))


def test_conflict_same_driver_overlapping_is_rejected(container):
    route, bus, driver = _setup(container)
    bus2 = Bus(2, "NW-2", 50)
    container.buses.add(bus2)
    container.schedule_service.create_schedule(route, bus, driver, TODAY, time(9, 0), time(11, 0))
    with pytest.raises(ScheduleError):       # same driver, overlapping time
        container.schedule_service.create_schedule(route, bus2, driver, TODAY, time(10, 0), time(12, 0))


def test_no_conflict_different_bus_and_driver(container):
    route, bus, driver = _setup(container)
    bus2 = Bus(2, "NW-2", 50)
    container.buses.add(bus2)
    driver2 = Driver(2, "D2", "L2", "active", TODAY + timedelta(days=365))
    container.drivers.add(driver2)
    container.schedule_service.create_schedule(route, bus, driver, TODAY, time(9, 0), time(11, 0))
    s2 = container.schedule_service.create_schedule(route, bus2, driver2, TODAY, time(9, 0), time(11, 0))
    assert s2 is not None


def test_back_to_back_same_bus_allowed(container):
    route, bus, driver = _setup(container)
    d2 = Driver(2, "D2", "L2", "active", TODAY + timedelta(days=365))
    container.drivers.add(d2)
    container.schedule_service.create_schedule(route, bus, driver, TODAY, time(9, 0), time(11, 0))
    s2 = container.schedule_service.create_schedule(route, bus, d2, TODAY, time(11, 0), time(13, 0))
    assert s2 is not None


def test_expired_licence_is_rejected(container):
    route, bus, _ = _setup(container)
    expired = Driver(9, "Old", "L9", "active", TODAY - timedelta(days=1))
    container.drivers.add(expired)
    with pytest.raises(ScheduleError):
        container.schedule_service.create_schedule(route, bus, expired, TODAY, time(9, 0), time(11, 0))


def test_arrival_before_departure_rejected(container):
    route, bus, driver = _setup(container)
    with pytest.raises(ScheduleError):
        container.schedule_service.create_schedule(route, bus, driver, TODAY, time(11, 0), time(9, 0))


def test_create_recurring_makes_multiple(container):
    route, bus, driver = _setup(container)
    made = container.schedule_service.create_recurring(
        route, bus, driver, TODAY, time(9, 0), time(11, 0), "weekly", 3)
    assert len(made) == 3
    assert len(container.schedule_service.list_schedules()) == 3


def test_cancel_schedule_removes_it(container):
    route, bus, driver = _setup(container)
    s = container.schedule_service.create_schedule(route, bus, driver, TODAY, time(9, 0), time(11, 0))
    container.schedule_service.cancel_schedule(s.schedule_id)
    assert len(container.schedule_service.list_schedules()) == 0


def test_reschedule_updates_times(container):
    route, bus, driver = _setup(container)
    s = container.schedule_service.create_schedule(route, bus, driver, TODAY, time(9, 0), time(11, 0))
    container.schedule_service.reschedule(s.schedule_id, TODAY, time(13, 0), time(15, 0))
    updated = container.schedule_service.list_schedules()[0]
    assert updated.departure_time == time(13, 0)
