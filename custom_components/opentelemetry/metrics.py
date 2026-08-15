"""Metric collection for the OpenTelemetry integration."""
from __future__ import annotations

from homeassistant.const import MATCH_ALL, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant
from homeassistant.setup import async_get_setup_timings

from opentelemetry.metrics import CallbackOptions, Meter, Observation

from .registry_info import resolve_area_name


class HomeAssistantMetrics:
    """Registers OpenTelemetry instruments backed by HA state."""

    def __init__(
        self,
        hass: HomeAssistant,
        meter: Meter,
        *,
        scope_system: bool,
        scope_entities: bool,
        include_domains: list[str],
        exclude_entities: list[str],
    ) -> None:
        self._hass = hass
        self._include_domains = set(include_domains)
        self._exclude_entities = set(exclude_entities)
        self._remove_listeners: list = []
        self._instruments: list = []

        if scope_system:
            self._events_counter = meter.create_counter(
                "homeassistant.events",
                description="Home Assistant bus events observed, by event type",
                unit="1",
            )
            self._remove_listeners.append(
                hass.bus.async_listen(MATCH_ALL, self._on_event)
            )
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.entities.count",
                    callbacks=[self._system_entity_count],
                    description="Entities known to Home Assistant, by domain",
                    unit="1",
                )
            )
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.entities.unavailable.count",
                    callbacks=[self._unavailable_entity_count],
                    description=(
                        "Entities in an unavailable or unknown state, by domain"
                    ),
                    unit="1",
                )
            )
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.config_entries.count",
                    callbacks=[self._config_entries_count],
                    description="Configured integrations, by domain and state",
                    unit="1",
                )
            )
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.setup.duration",
                    callbacks=[self._setup_duration],
                    description="Time spent setting up each integration domain",
                    unit="s",
                )
            )

        if scope_entities:
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.entity.state",
                    callbacks=[self._entity_states],
                    description="Numeric state value of Home Assistant entities",
                    unit="1",
                )
            )

    def _on_event(self, event: Event) -> None:
        self._events_counter.add(1, {"homeassistant.event.type": event.event_type})

    def _system_entity_count(self, options: CallbackOptions) -> list[Observation]:
        counts: dict[str, int] = {}
        for state in self._hass.states.async_all():
            counts[state.domain] = counts.get(state.domain, 0) + 1
        return [
            Observation(count, {"homeassistant.domain": domain})
            for domain, count in counts.items()
        ]

    def _unavailable_entity_count(
        self, options: CallbackOptions
    ) -> list[Observation]:
        counts: dict[str, int] = {}
        for state in self._hass.states.async_all():
            if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                counts[state.domain] = counts.get(state.domain, 0) + 1
        return [
            Observation(count, {"homeassistant.domain": domain})
            for domain, count in counts.items()
        ]

    def _config_entries_count(self, options: CallbackOptions) -> list[Observation]:
        counts: dict[tuple[str, str], int] = {}
        for entry in self._hass.config_entries.async_entries():
            key = (entry.domain, entry.state.value)
            counts[key] = counts.get(key, 0) + 1
        return [
            Observation(
                count,
                {
                    "homeassistant.domain": domain,
                    "homeassistant.config_entry.state": state,
                },
            )
            for (domain, state), count in counts.items()
        ]

    def _setup_duration(self, options: CallbackOptions) -> list[Observation]:
        timings = async_get_setup_timings(self._hass)
        return [
            Observation(seconds, {"homeassistant.domain": domain})
            for domain, seconds in timings.items()
        ]

    def _is_entity_included(self, entity_id: str, domain: str) -> bool:
        if entity_id in self._exclude_entities:
            return False
        if self._include_domains and domain not in self._include_domains:
            return False
        return True

    def _entity_states(self, options: CallbackOptions) -> list[Observation]:
        observations: list[Observation] = []
        for state in self._hass.states.async_all():
            if not self._is_entity_included(state.entity_id, state.domain):
                continue
            try:
                value = float(state.state)
            except (TypeError, ValueError):
                continue
            attributes = {
                "homeassistant.entity_id": state.entity_id,
                "homeassistant.domain": state.domain,
            }
            unit = state.attributes.get("unit_of_measurement")
            if unit:
                attributes["homeassistant.unit"] = unit
            area = resolve_area_name(self._hass, state.entity_id)
            if area:
                attributes["homeassistant.area"] = area
            observations.append(Observation(value, attributes))
        return observations

    def async_shutdown(self) -> None:
        """Remove event listeners registered by this collector."""
        for remove in self._remove_listeners:
            remove()
        self._remove_listeners.clear()
