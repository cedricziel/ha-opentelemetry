"""Metric collection for the OpenTelemetry integration."""
from __future__ import annotations

from homeassistant.core import Event, HomeAssistant

from opentelemetry.metrics import CallbackOptions, Meter, Observation


class HomeAssistantMetrics:
    """Registers OpenTelemetry observable instruments backed by HA state."""

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
        self._state_changed_total = 0
        self._service_call_total = 0
        self._remove_listeners: list = []
        self._instruments: list = []

        if scope_system:
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.entities.count",
                    callbacks=[self._system_entity_count],
                    description="Entities known to Home Assistant, by domain",
                )
            )
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.state_changed.count",
                    callbacks=[self._state_changed_count],
                    description="State changes observed since startup",
                    unit="1",
                )
            )
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.service_calls.count",
                    callbacks=[self._service_call_count],
                    description="Service calls observed since startup",
                    unit="1",
                )
            )
            self._remove_listeners.append(
                hass.bus.async_listen("state_changed", self._on_state_changed)
            )
            self._remove_listeners.append(
                hass.bus.async_listen("call_service", self._on_call_service)
            )

        if scope_entities:
            self._instruments.append(
                meter.create_observable_gauge(
                    "homeassistant.entity.state",
                    callbacks=[self._entity_states],
                    description="Numeric state value of Home Assistant entities",
                )
            )

    def _on_state_changed(self, event: Event) -> None:
        self._state_changed_total += 1

    def _on_call_service(self, event: Event) -> None:
        self._service_call_total += 1

    def _system_entity_count(
        self, options: CallbackOptions
    ) -> list[Observation]:
        counts: dict[str, int] = {}
        for state in self._hass.states.async_all():
            counts[state.domain] = counts.get(state.domain, 0) + 1
        return [
            Observation(count, {"homeassistant.domain": domain})
            for domain, count in counts.items()
        ]

    def _state_changed_count(self, options: CallbackOptions) -> list[Observation]:
        return [Observation(self._state_changed_total)]

    def _service_call_count(self, options: CallbackOptions) -> list[Observation]:
        return [Observation(self._service_call_total)]

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
            observations.append(Observation(value, attributes))
        return observations

    def async_shutdown(self) -> None:
        """Remove event listeners registered by this collector."""
        for remove in self._remove_listeners:
            remove()
        self._remove_listeners.clear()
