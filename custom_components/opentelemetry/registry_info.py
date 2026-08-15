"""Entity/device/area registry lookups shared by metrics and traces."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


def resolve_area_name(hass: HomeAssistant, entity_id: str) -> str | None:
    """Resolve the area name for an entity, via its device if needed."""
    entry = er.async_get(hass).async_get(entity_id)
    if entry is None:
        return None

    area_id = entry.area_id
    if area_id is None and entry.device_id is not None:
        device = dr.async_get(hass).async_get(entry.device_id)
        area_id = device.area_id if device is not None else None

    if area_id is None:
        return None

    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else None
