"""
services/schedule_service.py — Schedule Service (Tier 2).

Maps to "Manage Schedules" and the Schedule.checkConflict() operation.
A schedule clashes only if it overlaps in time AND shares a bus or driver.
Creating a schedule is rejected if it would conflict or if the driver's
licence is invalid.
"""

from __future__ import annotations

from datetime import date, time
from typing import List

from srmss.data.repositories import ScheduleRepository
from srmss.models import Bus, Driver, Route, Schedule


class ScheduleError(Exception):
    pass


class ScheduleService:
    def __init__(self, schedules: ScheduleRepository):
        self.schedules = schedules

    def list_schedules(self) -> List[Schedule]:
        return self.schedules.all()

    # -- recurring timetables (daily / weekly / monthly) ------------------
    def create_recurring(self, route: Route, bus: Bus, driver: Driver,
                         start_date: date, departure: time, arrival: time,
                         frequency: str = "daily", occurrences: int = 1) -> list:
        """
        Create several schedules at a fixed interval, supporting the brief's
        daily / weekly / monthly timetables. Each occurrence is conflict-checked;
        any that would clash is skipped and reported in the returned list.
        """
        from datetime import timedelta
        steps = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1),
                 "monthly": timedelta(days=30)}
        if frequency not in steps:
            raise ScheduleError("frequency must be daily, weekly or monthly")
        created = []
        current = start_date
        for _ in range(max(1, occurrences)):
            try:
                created.append(self.create_schedule(
                    route, bus, driver, current, departure, arrival))
            except ScheduleError:
                pass  # skip clashing occurrence, keep going
            current = current + steps[frequency]
        return created

    # -- adjustments: cancel / reschedule ---------------------------------
    def cancel_schedule(self, schedule_id: int) -> None:
        if self.schedules.get(schedule_id) is None:
            raise ScheduleError(f"No schedule with id {schedule_id}")
        self.schedules.delete(schedule_id)

    def reschedule(self, schedule_id: int, sched_date: date,
                   departure: time, arrival: time) -> Schedule:
        existing = self.schedules.get(schedule_id)
        if existing is None:
            raise ScheduleError(f"No schedule with id {schedule_id}")
        if arrival <= departure:
            raise ScheduleError("Arrival time must be after departure time")
        # Build the proposed version and check against all OTHERS.
        proposed = Schedule(schedule_id, existing.route, existing.bus,
                            existing.driver, sched_date, departure, arrival)
        others = [s for s in self.schedules.all() if s.schedule_id != schedule_id]
        if proposed.check_conflict(others):
            raise ScheduleError("Rescheduled time conflicts with another schedule")
        self.schedules.update_times(schedule_id, sched_date, departure, arrival)
        return proposed

    def create_schedule(self, route: Route, bus: Bus, driver: Driver,
                        sched_date: date, departure: time, arrival: time) -> Schedule:
        """Create a schedule after checking licence validity and conflicts."""
        if arrival <= departure:
            raise ScheduleError("Arrival time must be after departure time")
        if not driver.license_valid(sched_date):
            raise ScheduleError(f"Driver {driver.name}'s licence is not valid")

        candidate = Schedule(self.schedules.next_id(), route, bus, driver,
                             sched_date, departure, arrival)
        if candidate.check_conflict(self.schedules.all()):
            raise ScheduleError(
                "Schedule conflicts with an existing one (same bus or driver, "
                "overlapping time)")
        self.schedules.add(candidate)
        return candidate

    # -- single-resource availability (used by RouteService) -------------
    def is_bus_free(self, bus: Bus, sched_date: date,
                    departure: time, arrival: time) -> bool:
        existing = [s for s in self.schedules.all()
                    if s.date == sched_date and s.bus.bus_id == bus.bus_id]
        for s in existing:
            if departure < s.arrival_time and s.departure_time < arrival:
                return False
        return True

    def is_driver_free(self, driver: Driver, sched_date: date,
                       departure: time, arrival: time) -> bool:
        existing = [s for s in self.schedules.all()
                    if s.date == sched_date and s.driver.driver_id == driver.driver_id]
        for s in existing:
            if departure < s.arrival_time and s.departure_time < arrival:
                return False
        return True
