"""Fixtures shared by the OpenTelemetry integration tests."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow this custom component to be loaded during tests."""
    yield
