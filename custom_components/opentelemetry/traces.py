"""Trace instrumentation for the OpenTelemetry integration.

Home Assistant does not expose a public hook around service-call or
automation-run completion, so these are point-in-time spans
(``start_time == end_time``) marking that something happened, not spans
covering the full duration of executing it. ``EVENT_AUTOMATION_TRIGGERED``
is hardcoded rather than imported from ``homeassistant.components.automation``
to avoid a hard import-time dependency on that component.
"""
from __future__ import annotations

import time

from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME, EVENT_CALL_SERVICE
from homeassistant.core import Event, HomeAssistant

from opentelemetry.trace import Tracer

from .registry_info import resolve_area_name

EVENT_AUTOMATION_TRIGGERED = "automation_triggered"
ATTR_SOURCE = "source"


class HomeAssistantTracing:
    """Emits spans for service calls, automation runs, and state changes."""

    def __init__(
        self,
        hass: HomeAssistant,
        tracer: Tracer,
        *,
        scope_system: bool,
        scope_entities: bool,
        enable_state_changed_traces: bool,
        include_domains: list[str],
        exclude_entities: list[str],
    ) -> None:
        self._hass = hass
        self._tracer = tracer
        self._scope_entities = scope_entities
        self._include_domains = set(include_domains)
        self._exclude_entities = set(exclude_entities)
        self._remove_listeners: list = []

        if scope_system:
            self._remove_listeners.append(
                hass.bus.async_listen(EVENT_CALL_SERVICE, self._on_call_service)
            )
            self._remove_listeners.append(
                hass.bus.async_listen(
                    EVENT_AUTOMATION_TRIGGERED, self._on_automation_triggered
                )
            )
        if scope_entities and enable_state_changed_traces:
            self._remove_listeners.append(
                hass.bus.async_listen("state_changed", self._on_state_changed)
            )

    @staticmethod
    def _context_attributes(event: Event) -> dict[str, str]:
        context = event.context
        attributes = {}
        if context.id:
            attributes["homeassistant.context.id"] = context.id
        if context.parent_id:
            attributes["homeassistant.context.parent_id"] = context.parent_id
        if context.user_id:
            attributes["homeassistant.context.user_id"] = context.user_id
        return attributes

    def _is_entity_included(self, entity_id: str) -> bool:
        if entity_id in self._exclude_entities:
            return False
        if self._include_domains:
            domain = entity_id.split(".", 1)[0]
            if domain not in self._include_domains:
                return False
        return True

    def _on_call_service(self, event: Event) -> None:
        domain = event.data.get("domain")
        service = event.data.get("service")
        now = time.time_ns()
        span = self._tracer.start_span(
            f"service_call {domain}.{service}", start_time=now
        )
        span.set_attribute("homeassistant.service.domain", domain)
        span.set_attribute("homeassistant.service.name", service)
        for key, value in self._context_attributes(event).items():
            span.set_attribute(key, value)
        if self._scope_entities:
            target = (event.data.get("service_data") or {}).get("entity_id")
            if isinstance(target, str) and self._is_entity_included(target):
                span.set_attribute("homeassistant.entity_id", target)
                area = resolve_area_name(self._hass, target)
                if area:
                    span.set_attribute("homeassistant.area", area)
            elif target:
                included = [t for t in target if self._is_entity_included(t)]
                if included:
                    span.set_attribute("homeassistant.target.entity_ids", included)
        span.end(end_time=now)

    def _on_automation_triggered(self, event: Event) -> None:
        entity_id = event.data.get(ATTR_ENTITY_ID)
        now = time.time_ns()
        span = self._tracer.start_span(
            f"automation_triggered {entity_id}", start_time=now
        )
        span.set_attribute("homeassistant.entity_id", entity_id)
        name = event.data.get(ATTR_NAME)
        if name:
            span.set_attribute("homeassistant.automation.name", name)
        source = event.data.get(ATTR_SOURCE)
        if source:
            span.set_attribute("homeassistant.automation.source", source)
        for key, value in self._context_attributes(event).items():
            span.set_attribute(key, value)
        span.end(end_time=now)

    def _on_state_changed(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        entity_id = event.data.get("entity_id")
        if not self._is_entity_included(entity_id):
            return
        old_state = event.data.get("old_state")
        now = time.time_ns()
        span = self._tracer.start_span(f"state_changed {entity_id}", start_time=now)
        span.set_attribute("homeassistant.entity_id", entity_id)
        span.set_attribute("homeassistant.new_state", new_state.state)
        if old_state is not None:
            span.set_attribute("homeassistant.old_state", old_state.state)
        area = resolve_area_name(self._hass, entity_id)
        if area:
            span.set_attribute("homeassistant.area", area)
        for key, value in self._context_attributes(event).items():
            span.set_attribute(key, value)
        span.end(end_time=now)

    def async_shutdown(self) -> None:
        """Remove event listeners registered by this instrumentor."""
        for remove in self._remove_listeners:
            remove()
        self._remove_listeners.clear()
