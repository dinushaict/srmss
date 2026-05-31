# SRMSS — Smart Route Management & Scheduling System

Coursework implementation for **CS6003 Advanced Software Engineering**
(London Metropolitan University). SRMSS digitalises route planning and
scheduling for public-transport depots: it manages routes, schedules, the
vehicle fleet, drivers, trip status, fuel and maintenance logs, and produces
fleet reports as PDF.

> **Group members:** _add your IDs, surnames and first names here._

## Architecture (3-Tier)

The code is organised to match the 3-Tier Architecture diagram:

```
Tier 1  Presentation   webapp/            Flask web app (login + dashboard + schedules)
Tier 2  Business Logic srmss/services/    AuthService, RouteService, ScheduleService,
                                          FleetService, ReportingService
Tier 3  Data           srmss/data/        SQLite database + repositories
        Domain model   srmss/models.py    the classes from the Class Diagram
```

The presentation tier contains **no business rules** — it only calls services.
Services contain the rules and talk to the data tier through repositories.

## How the code maps to the UML

**Class Diagram → `srmss/models.py`**

| Class | Key attributes | Methods (UML → code) |
|-------|----------------|----------------------|
| `User` (abstract) | userId, username, password, role | login()→`login`, logout()→`logout` |
| `Administrator`, `Supervisor`, `Clerk` | inherit `User` | — |
| `Driver` | driverId, name, licenseNo, status | getDetails()→`get_details`, updateInfo()→`update_info` |
| `Bus` | regNo, capacity, type, status | getDetails()→`get_details`, updateStatus()→`update_status` |
| `Route` | routeId, startPoint, endPoint, distance | addStop()→`add_stop`, getMapData()→`get_map_data` |
| `Schedule` | scheduleId, date, departureTime, arrivalTime | checkConflict()→`check_conflict` |
| `Trip` | tripId, status, actualDeparture, actualArrival | updateStatus()→`update_status`, complete()→`complete` |
| `FuelLog` | logId, date, quantity, cost | record()→`record` |
| `MaintenanceLog` | logId, date, type, cost | record()→`record` |
| `Report` | reportId, type, dateRange, generatedAt | generate()→`fleet_report`, exportPDF()→`export_pdf` |

**Use Case Diagram → services**

| Use case | Where |
|----------|-------|
| Login | `AuthService.login` |
| Manage Routes | `RouteService.create_route` / `list_routes` |
| Assign Bus / Driver | `RouteService.is_bus_available` / `is_driver_available` |
| Manage Schedules | `ScheduleService.create_schedule` (rejects conflicts) |
| Monitor / Update Trip Status | `FleetService.list_trips` / `update_trip_status` |
| Manage Vehicles / Drivers | `FleetService.list_buses` / `list_drivers` |
| Log Fuel Usage | `FleetService.log_fuel` |
| Log Maintenance | `FleetService.log_maintenance` |
| View Dashboard | `webapp` dashboard + `ReportingService.trip_summary` |
| Generate Reports | `ReportingService.fleet_report` / `export_pdf` |

## Requirements

- Python 3.10+
- Packages in `requirements.txt` (Flask, fpdf2, pytest). SQLite is built into
  Python — no database server to install.

## Setup

```bash
# from the project root (the folder with this README)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
python -m pip install -r requirements.txt
```

## Run the tests

```bash
# Windows PowerShell:
$env:PYTHONPATH="."
python -m pytest tests/ -v

# macOS / Linux:
PYTHONPATH=. python -m pytest tests/ -v
```

All tests should pass (black-box tests across all five services plus the web app).

## Run the web app

```bash
python run.py
```

Open <http://127.0.0.1:5000> and sign in with a demo account:

| Role | Username | Password |
|------|----------|----------|
| Administrator | `admin` | `depot123` |
| Supervisor | `supervisor` | `super123` |
| Clerk | `clerk` | `clerk123` |

From the dashboard you can view fleet stats, update trip status, open the
**Schedules** page (try adding a clashing schedule — it will be rejected), and
**Download PDF** to get the fleet report. Press `Ctrl+C` to stop the server.

> Demo data is loaded into an in-memory SQLite database at start-up
> (`srmss/container.py → seed_demo`); restarting the server resets it.

## Testing approach

Black-box unit tests (`tests/`) drive each service through its public methods
and assert outputs — for example, that conflicting schedules are rejected, that
fuel efficiency is computed correctly, and that the PDF export produces a valid
file. Each test runs against a fresh in-memory database.

## Functional coverage (brief — six modules)

| Module | Requirement | Implemented in |
|--------|-------------|----------------|
| 1 Route Planning | Create / modify / manage routes (start, end, stops, distance) | `RouteService.create_route` / `update_route`; Routes page |
| 1 | Assign by capacity, availability, service type | `RouteService.suitable_buses`, `is_bus_available`, `is_driver_available` |
| 1 | Online map integration | `Route.get_map_data` → Google Maps directions link (Routes page) |
| 2 Schedule Management | Departure/arrival times, daily/weekly/monthly | `ScheduleService.create_schedule` / `create_recurring` |
| 2 | Detect & prevent conflicts | `Schedule.check_conflict`, `ScheduleService.create_schedule` |
| 2 | Adjustments (emergencies/maintenance) | `ScheduleService.cancel_schedule` / `reschedule` |
| 3 Dashboard | Active routes, buses, drivers overview | Dashboard page |
| 3 | Real-time trip status | `FleetService.update_trip_status`; Dashboard |
| 3 | Summary stats incl. vehicle utilisation | `ReportingService.trip_summary` / `vehicle_utilisation` |
| 4 Fuel & Maintenance | Fuel consumption per vehicle | `FleetService.log_fuel`, `fuel_efficiency` |
| 4 | Routine/corrective maintenance | `FleetService.log_maintenance`; history on Fleet page |
| 4 | Summary reports | `ReportingService.fleet_report` |
| 5 Driver & Vehicle DB | Driver details, licence validity, assigned routes, working hours | `Driver`, `ReportingService.driver_routes` / `driver_working_hours` |
| 5 | Vehicle reg, capacity, mileage, maintenance history | `Bus`, fuel odometer, maintenance history (Fleet page) |
| 6 Reporting & Analytics | Trip completion, route performance | `ReportingService.route_performance` / `trip_summary` |
| 6 | Exportable PDF | `ReportingService.export_pdf` |

> Note on mapping: a real Google Maps **embed** needs an API key; SRMSS uses a
> no-key directions **link** so it works from any browser. This is a reasonable
> coursework-level integration and can be extended to a full embed later.
