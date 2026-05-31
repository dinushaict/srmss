"""Shared fixtures: fresh in-memory containers for each test."""

import pytest

from srmss.container import build_container, seed_demo


@pytest.fixture
def container():
    """Empty in-memory database with all tiers wired up."""
    return build_container(":memory:")


@pytest.fixture
def seeded():
    """In-memory container pre-loaded with the demo data."""
    c = build_container(":memory:")
    seed_demo(c)
    return c
