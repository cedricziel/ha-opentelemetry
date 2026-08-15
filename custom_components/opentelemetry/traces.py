"""Trace instrumentation for the OpenTelemetry integration.

Home Assistant does not expose a public hook around service-call
completion, so these are point-in-time spans (``start_time == end_time``)
marking that a call or state change happened, not spans covering the full
duration of executing it.
"""
from __future__ import annotations

import time

from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import Event, HomeAssistant

from opentelemetry.trace import Tracer


class HomeAssistantTracing:
    """Emits OpenTelemetry spans for service calls and entity state changes."""

    def __init__(
        self,
        hass: HomeAssistant,
        tracer: Tracer,
        *,
        scope_system: bool,
        scope_entities: bool,
    ) -> None:
        self._tracer = tracer
        self._scope_entities = scope_entities
        self._remove_listeners: list = []

        if scope_system:
            self._remove_listeners.append(
                hass.bus.async_listen(EVENT_CALL_SERVICE, self._on_call_service)
            )
        if scope_entities:
            self._remove_listeners.append(
                hass.bus.async_listen("state_changed", self._on_state_changed)
            )

    def _on_call_service(self, event: Event) -> None:
        domain = event.data.get("domain")
        service = event.data.get("service")
        now = time.time_ns()
        span = self._tracer.start_span(
            f"service_call {domain}.{service}", start_time=now
        )
        span.set_attribute("homeassistant.service.domain", domain)
        span.set_attribute("homeassistant.service.name", service)
        if self._scope_entities:
            target = (event.data.get("service_data") or {}).get("entity_id")
            if target:
                if isinstance(target, str):
                    span.set_attribute("homeassistant.entity_id", target)
                else:
                    span.set_attribute("homeassistant.entity_id", list(target))
        span.end(end_time=now)

    def _on_state_changed(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        old_state = event.data.get("old_state")
        entity_id = event.data.get("entity_id")
        now = time.time_ns()
        span = self._tracer.start_span(f"state_changed {entity_id}", start_time=now)
        span.set_attribute("homeassistant.entity_id", entity_id)
        span.set_attribute("homeassistant.new_state", new_state.state)
        if old_state is not None:
            span.set_attribute("homeassistant.old_state", old_state.state)
        span.end(end_time=now)

    def async_shutdown(self) -> None:
        """Remove event listeners registered by this instrumentor."""
        for remove in self._remove_listeners:
            remove()
        self._remove_listeners.clear()
