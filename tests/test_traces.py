"""Tests for service-call and entity state-change tracing."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from custom_components.opentelemetry.traces import HomeAssistantTracing


def _tracer_with_memory_exporter() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


async def test_service_call_emits_span_with_entity_id(hass: HomeAssistant) -> None:
    """A service call targeting an entity produces a span with that entity_id."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = HomeAssistantTracing(
        hass, tracer, scope_system=True, scope_entities=True
    )

    hass.states.async_set("light.kitchen", "off")
    hass.services.async_register("light", "turn_on", lambda call: None)
    await hass.services.async_call(
        "light", "turn_on", {"entity_id": "light.kitchen"}, blocking=True
    )
    await hass.async_block_till_done()

    spans = [
        span
        for span in exporter.get_finished_spans()
        if span.name == "service_call light.turn_on"
    ]
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes["homeassistant.service.domain"] == "light"
    assert span.attributes["homeassistant.service.name"] == "turn_on"
    assert span.attributes["homeassistant.entity_id"] == "light.kitchen"
    assert span.start_time == span.end_time

    tracing.async_shutdown()


async def test_state_changed_emits_span(hass: HomeAssistant) -> None:
    """A state change produces a span carrying old/new state."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = HomeAssistantTracing(
        hass, tracer, scope_system=False, scope_entities=True
    )

    hass.states.async_set("sensor.temp", "20")
    await hass.async_block_till_done()
    exporter.clear()

    hass.states.async_set("sensor.temp", "21")
    await hass.async_block_till_done()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "state_changed sensor.temp"
    assert span.attributes["homeassistant.new_state"] == "21"
    assert span.attributes["homeassistant.old_state"] == "20"

    tracing.async_shutdown()


async def test_shutdown_removes_listeners(hass: HomeAssistant) -> None:
    """After shutdown, no further spans are emitted."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = HomeAssistantTracing(
        hass, tracer, scope_system=True, scope_entities=True
    )
    tracing.async_shutdown()

    hass.states.async_set("sensor.temp", "20")
    await hass.async_block_till_done()

    assert exporter.get_finished_spans() == ()
