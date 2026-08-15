"""Tests for entity/system metric collection."""
from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from opentelemetry.metrics import CallbackOptions

from custom_components.opentelemetry.metrics import HomeAssistantMetrics


async def test_entity_state_observation_skips_non_numeric(
    hass: HomeAssistant,
) -> None:
    """Only numeric states are emitted as gauge observations."""
    hass.states.async_set("sensor.temp", "21.5", {"unit_of_measurement": "°C"})
    hass.states.async_set("light.kitchen", "on")
    await hass.async_block_till_done()

    meter = MagicMock()
    collector = HomeAssistantMetrics(
        hass,
        meter,
        scope_system=False,
        scope_entities=True,
        include_domains=[],
        exclude_entities=[],
    )

    callback = meter.create_observable_gauge.call_args.kwargs["callbacks"][0]
    observations = callback(CallbackOptions())

    assert len(observations) == 1
    assert observations[0]._value == 21.5
    assert observations[0]._attributes["homeassistant.entity_id"] == "sensor.temp"
    assert observations[0]._attributes["homeassistant.unit"] == "°C"

    collector.async_shutdown()


async def test_exclude_entities_filter(hass: HomeAssistant) -> None:
    """Excluded entities are never observed even if numeric."""
    hass.states.async_set("sensor.temp", "21.5")
    await hass.async_block_till_done()

    meter = MagicMock()
    collector = HomeAssistantMetrics(
        hass,
        meter,
        scope_system=False,
        scope_entities=True,
        include_domains=[],
        exclude_entities=["sensor.temp"],
    )

    callback = meter.create_observable_gauge.call_args.kwargs["callbacks"][0]
    observations = callback(CallbackOptions())

    assert observations == []
    collector.async_shutdown()


async def test_include_domains_filter(hass: HomeAssistant) -> None:
    """Only entities from included domains are observed when the filter is set."""
    hass.states.async_set("sensor.temp", "21.5")
    hass.states.async_set("counter.visits", "3")
    await hass.async_block_till_done()

    meter = MagicMock()
    collector = HomeAssistantMetrics(
        hass,
        meter,
        scope_system=False,
        scope_entities=True,
        include_domains=["sensor"],
        exclude_entities=[],
    )

    callback = meter.create_observable_gauge.call_args.kwargs["callbacks"][0]
    observations = callback(CallbackOptions())

    assert len(observations) == 1
    assert observations[0]._attributes["homeassistant.entity_id"] == "sensor.temp"

    collector.async_shutdown()
