"""Tests for setting up and unloading the OpenTelemetry config entry."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.opentelemetry.const import (
    CONF_AUTH_HEADER,
    CONF_DATASET_ID,
    CONF_ENDPOINT,
    CONF_INSECURE,
    CONF_PROTOCOL,
    CONF_SERVICE_NAME,
    CONF_TENANT_ID,
    DOMAIN,
    PROTOCOL_GRPC,
)

ENTRY_DATA = {
    CONF_ENDPOINT: "192.168.178.6:4317",
    CONF_PROTOCOL: PROTOCOL_GRPC,
    CONF_INSECURE: True,
    CONF_AUTH_HEADER: "Bearer sk-test",
    CONF_TENANT_ID: "homelab",
    CONF_DATASET_ID: "",
    CONF_SERVICE_NAME: "homeassistant",
}


@pytest.fixture
def mock_exporters():
    """Prevent real OTLP exporters from being constructed during setup."""
    with (
        patch(
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter",
            return_value=MagicMock(),
        ),
        patch(
            "opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter",
            return_value=MagicMock(),
        ),
        patch(
            "opentelemetry.exporter.otlp.proto.grpc._log_exporter.OTLPLogExporter",
            return_value=MagicMock(),
        ),
    ):
        yield


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_exporters: None
) -> None:
    """The entry sets up all enabled providers and tears them down cleanly."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime = hass.data[DOMAIN][entry.entry_id]
    assert "tracer_provider" in runtime
    assert "meter_provider" in runtime
    assert "logger_provider" in runtime
    assert "tracing" in runtime
    assert "metrics" in runtime

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_service_calls_work_normally_after_setup_and_unload(
    hass: HomeAssistant, mock_exporters: None
) -> None:
    """Instrumenting service calls and state changes doesn't break either."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    calls = []
    hass.services.async_register("test", "noop", lambda call: calls.append(call))
    await hass.services.async_call("test", "noop", {}, blocking=True)
    assert len(calls) == 1
    hass.states.async_set("sensor.temp", "21.5")
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Listeners are gone, but calling a service still works fine.
    await hass.services.async_call("test", "noop", {}, blocking=True)
    assert len(calls) == 2
