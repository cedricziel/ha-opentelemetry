"""Tests for service-call, automation, and state-change tracing."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from custom_components.opentelemetry.traces import (
    EVENT_AUTOMATION_TRIGGERED,
    HomeAssistantTracing,
)


def _tracer_with_memory_exporter() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def _tracing(hass, tracer, **overrides):
    defaults = {
        "scope_system": True,
        "scope_entities": True,
        "enable_state_changed_traces": False,
        "include_domains": [],
        "exclude_entities": [],
    }
    defaults.update(overrides)
    return HomeAssistantTracing(hass, tracer, **defaults)


async def test_service_call_emits_span_with_entity_id_and_context(
    hass: HomeAssistant,
) -> None:
    """A service call targeting one entity produces a span with entity_id/context."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = _tracing(hass, tracer)

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
    assert span.attributes["homeassistant.context.id"]
    assert span.start_time == span.end_time

    tracing.async_shutdown()


async def test_service_call_with_multiple_entities_uses_target_attribute(
    hass: HomeAssistant,
) -> None:
    """A multi-entity service call uses target.entity_ids, not entity_id."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = _tracing(hass, tracer)

    hass.states.async_set("light.a", "off")
    hass.states.async_set("light.b", "off")
    hass.services.async_register("light", "turn_on", lambda call: None)
    await hass.services.async_call(
        "light", "turn_on", {"entity_id": ["light.a", "light.b"]}, blocking=True
    )
    await hass.async_block_till_done()

    spans = [
        span
        for span in exporter.get_finished_spans()
        if span.name == "service_call light.turn_on"
    ]
    assert len(spans) == 1
    span = spans[0]
    assert "homeassistant.entity_id" not in span.attributes
    assert list(span.attributes["homeassistant.target.entity_ids"]) == [
        "light.a",
        "light.b",
    ]

    tracing.async_shutdown()


async def test_automation_triggered_emits_span(hass: HomeAssistant) -> None:
    """An automation_triggered event produces a span with name/source."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = _tracing(hass, tracer)

    hass.bus.async_fire(
        EVENT_AUTOMATION_TRIGGERED,
        {
            "entity_id": "automation.night_mode",
            "name": "Night mode",
            "source": "state of binary_sensor.dark",
        },
    )
    await hass.async_block_till_done()

    spans = [
        span
        for span in exporter.get_finished_spans()
        if span.name == "automation_triggered automation.night_mode"
    ]
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes["homeassistant.entity_id"] == "automation.night_mode"
    assert span.attributes["homeassistant.automation.name"] == "Night mode"
    assert (
        span.attributes["homeassistant.automation.source"]
        == "state of binary_sensor.dark"
    )

    tracing.async_shutdown()


async def test_state_changed_spans_are_off_by_default(hass: HomeAssistant) -> None:
    """State-changed spans are not emitted unless explicitly enabled."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = _tracing(hass, tracer, enable_state_changed_traces=False)

    hass.states.async_set("sensor.temp", "20")
    await hass.async_block_till_done()

    assert exporter.get_finished_spans() == ()
    tracing.async_shutdown()


async def test_state_changed_emits_span_with_area_when_enabled(
    hass: HomeAssistant,
) -> None:
    """When enabled, a state change produces a span with old/new state and area."""
    area = ar.async_get(hass).async_get_or_create("Kitchen")
    entry = er.async_get(hass).async_get_or_create(
        "sensor", "test", "unique1", suggested_object_id="temp"
    )
    er.async_get(hass).async_update_entity(entry.entity_id, area_id=area.id)

    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = _tracing(hass, tracer, enable_state_changed_traces=True)

    hass.states.async_set(entry.entity_id, "20")
    await hass.async_block_till_done()
    exporter.clear()

    hass.states.async_set(entry.entity_id, "21")
    await hass.async_block_till_done()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == f"state_changed {entry.entity_id}"
    assert span.attributes["homeassistant.new_state"] == "21"
    assert span.attributes["homeassistant.old_state"] == "20"
    assert span.attributes["homeassistant.area"] == "Kitchen"

    tracing.async_shutdown()


async def test_state_changed_respects_exclude_filter(hass: HomeAssistant) -> None:
    """Excluded entities produce no state-changed span even when enabled."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = _tracing(
        hass,
        tracer,
        enable_state_changed_traces=True,
        exclude_entities=["sensor.temp"],
    )

    hass.states.async_set("sensor.temp", "20")
    await hass.async_block_till_done()

    assert exporter.get_finished_spans() == ()
    tracing.async_shutdown()


async def test_shutdown_removes_listeners(hass: HomeAssistant) -> None:
    """After shutdown, no further spans are emitted."""
    provider, exporter = _tracer_with_memory_exporter()
    tracer = provider.get_tracer("test")
    tracing = _tracing(hass, tracer, enable_state_changed_traces=True)
    tracing.async_shutdown()

    hass.states.async_set("sensor.temp", "20")
    await hass.async_block_till_done()

    assert exporter.get_finished_spans() == ()
