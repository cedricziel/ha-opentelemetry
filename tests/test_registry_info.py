"""Tests for entity/device/area registry resolution."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.opentelemetry.registry_info import resolve_area_name


async def test_resolve_area_name_via_entity(hass: HomeAssistant) -> None:
    """An entity with a direct area assignment resolves to that area."""
    area = ar.async_get(hass).async_get_or_create("Kitchen")
    entry = er.async_get(hass).async_get_or_create(
        "sensor", "test", "unique1", suggested_object_id="temp"
    )
    er.async_get(hass).async_update_entity(entry.entity_id, area_id=area.id)

    assert resolve_area_name(hass, entry.entity_id) == "Kitchen"


async def test_resolve_area_name_via_device(hass: HomeAssistant) -> None:
    """An entity with no direct area falls back to its device's area."""
    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_hass(hass)

    area = ar.async_get(hass).async_get_or_create("Garage")
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("test", "device1")},
    )
    dr.async_get(hass).async_update_device(device.id, area_id=area.id)

    entry = er.async_get(hass).async_get_or_create(
        "sensor",
        "test",
        "unique2",
        suggested_object_id="humidity",
        device_id=device.id,
        config_entry=config_entry,
    )

    assert resolve_area_name(hass, entry.entity_id) == "Garage"


async def test_resolve_area_name_returns_none_when_unassigned(
    hass: HomeAssistant,
) -> None:
    """An entity with no area, directly or via device, resolves to None."""
    entry = er.async_get(hass).async_get_or_create(
        "sensor", "test", "unique3", suggested_object_id="unassigned"
    )
    assert resolve_area_name(hass, entry.entity_id) is None


async def test_resolve_area_name_unknown_entity(hass: HomeAssistant) -> None:
    """An entity not in the registry at all resolves to None."""
    assert resolve_area_name(hass, "sensor.not_registered") is None
