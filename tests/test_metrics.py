"""Tests for entity/system metric collection."""
from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from opentelemetry.metrics import CallbackOptions
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


async def test_entity_state_includes_area(hass: HomeAssistant) -> None:
    """Entities assigned to an area carry it as an attribute."""
    area = ar.async_get(hass).async_get_or_create("Kitchen")
    entry = er.async_get(hass).async_get_or_create(
        "sensor", "test", "unique1", suggested_object_id="temp"
    )
    er.async_get(hass).async_update_entity(entry.entity_id, area_id=area.id)
    hass.states.async_set(entry.entity_id, "21.5")
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
    assert observations[0]._attributes["homeassistant.area"] == "Kitchen"

    collector.async_shutdown()


async def test_events_counter_increments_by_event_type(hass: HomeAssistant) -> None:
    """Every bus event increments the counter, attributed by event type."""
    meter = MagicMock()
    collector = HomeAssistantMetrics(
        hass,
        meter,
        scope_system=True,
        scope_entities=False,
        include_domains=[],
        exclude_entities=[],
    )

    hass.bus.async_fire("some_custom_event")
    await hass.async_block_till_done()

    counter = meter.create_counter.return_value
    counter.add.assert_any_call(1, {"homeassistant.event.type": "some_custom_event"})

    collector.async_shutdown()


async def test_unavailable_entity_count(hass: HomeAssistant) -> None:
    """Unavailable/unknown entities are counted by domain."""
    hass.states.async_set("sensor.a", "unavailable")
    hass.states.async_set("sensor.b", "unknown")
    hass.states.async_set("sensor.c", "21.5")
    await hass.async_block_till_done()

    meter = MagicMock()
    collector = HomeAssistantMetrics(
        hass,
        meter,
        scope_system=True,
        scope_entities=False,
        include_domains=[],
        exclude_entities=[],
    )

    calls = meter.create_observable_gauge.call_args_list
    unavailable_call = next(
        c for c in calls if c.args[0] == "homeassistant.entities.unavailable.count"
    )
    callback = unavailable_call.kwargs["callbacks"][0]
    observations = callback(CallbackOptions())

    assert len(observations) == 1
    assert observations[0]._value == 2
    assert observations[0]._attributes["homeassistant.domain"] == "sensor"

    collector.async_shutdown()


async def test_config_entries_count(hass: HomeAssistant) -> None:
    """Config entries are counted by domain and state."""
    entry = MockConfigEntry(domain="test_domain")
    entry.add_to_hass(hass)

    meter = MagicMock()
    collector = HomeAssistantMetrics(
        hass,
        meter,
        scope_system=True,
        scope_entities=False,
        include_domains=[],
        exclude_entities=[],
    )

    calls = meter.create_observable_gauge.call_args_list
    entries_call = next(
        c for c in calls if c.args[0] == "homeassistant.config_entries.count"
    )
    callback = entries_call.kwargs["callbacks"][0]
    observations = callback(CallbackOptions())

    matching = [
        o
        for o in observations
        if o._attributes["homeassistant.domain"] == "test_domain"
    ]
    assert len(matching) == 1
    assert matching[0]._value == 1
    assert matching[0]._attributes["homeassistant.config_entry.state"] == "not_loaded"

    collector.async_shutdown()
