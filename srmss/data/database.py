"""
data/database.py — Tier 3 (Data).

A thin wrapper around Python's built-in sqlite3. No external database server is
needed; data lives in a single .db file (or fully in memory for tests). This
realises the relational Data tier shown in the 3-Tier Architecture diagram.
"""

from __future__ import annotations

import sqlite3
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    username  TEXT UNIQUE NOT NULL,
    password  TEXT NOT NULL,
    salt      TEXT NOT NULL,
    role      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drivers (
    driver_id      INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    license_no     TEXT NOT NULL,
    status         TEXT NOT NULL,
    license_expiry TEXT
);
CREATE TABLE IF NOT EXISTS buses (
    bus_id   INTEGER PRIMARY KEY,
    reg_no   TEXT UNIQUE NOT NULL,
    capacity INTEGER NOT NULL,
    type     TEXT NOT NULL,
    status   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS routes (
    route_id    INTEGER PRIMARY KEY,
    start_point TEXT NOT NULL,
    end_point   TEXT NOT NULL,
    distance    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS stops (
    stop_id  INTEGER PRIMARY KEY,
    route_id INTEGER NOT NULL,
    name     TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id    INTEGER PRIMARY KEY,
    route_id       INTEGER NOT NULL,
    bus_id         INTEGER NOT NULL,
    driver_id      INTEGER NOT NULL,
    date           TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    arrival_time   TEXT NOT NULL,
    FOREIGN KEY (route_id)  REFERENCES routes(route_id),
    FOREIGN KEY (bus_id)    REFERENCES buses(bus_id),
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
);
CREATE TABLE IF NOT EXISTS trips (
    trip_id          INTEGER PRIMARY KEY,
    schedule_id      INTEGER NOT NULL,
    status           TEXT NOT NULL,
    actual_departure TEXT,
    actual_arrival   TEXT,
    FOREIGN KEY (schedule_id) REFERENCES schedules(schedule_id)
);
CREATE TABLE IF NOT EXISTS fuel_logs (
    log_id   INTEGER PRIMARY KEY,
    bus_id   INTEGER NOT NULL,
    date     TEXT NOT NULL,
    quantity REAL NOT NULL,
    cost     REAL NOT NULL,
    odometer INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
);
CREATE TABLE IF NOT EXISTS maintenance_logs (
    log_id INTEGER PRIMARY KEY,
    bus_id INTEGER NOT NULL,
    date   TEXT NOT NULL,
    type   TEXT NOT NULL,
    cost   REAL NOT NULL,
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
);
"""


class Database:
    """Owns a single sqlite3 connection and creates the schema on demand."""

    def __init__(self, path: str = ":memory:"):
        # check_same_thread=False lets Flask's dev server share the connection.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def init_schema(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql: str, params: tuple = ()) -> list:
        return self.conn.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()

    def close(self) -> None:
        self.conn.close()
