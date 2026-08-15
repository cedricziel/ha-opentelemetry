"""Tests for log forwarding and enrichment."""
from __future__ import annotations

import logging

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)

from custom_components.opentelemetry.logs import attach_log_handler, detach_log_handler


def _provider_with_exporter() -> tuple[LoggerProvider, InMemoryLogRecordExporter]:
    exporter = InMemoryLogRecordExporter()
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    return provider, exporter


def test_domain_enrichment_for_core_component() -> None:
    """A homeassistant.components.<domain> logger gets a domain attribute."""
    provider, exporter = _provider_with_exporter()
    handler = attach_log_handler(provider)
    try:
        logging.getLogger("homeassistant.components.mqtt.client").info("hello")
    finally:
        detach_log_handler(handler)

    logs = exporter.get_finished_logs()
    assert len(logs) == 1
    assert logs[0].log_record.attributes["homeassistant.domain"] == "mqtt"


def test_domain_enrichment_for_custom_component() -> None:
    """A custom_components.<domain> logger gets a domain attribute."""
    provider, exporter = _provider_with_exporter()
    handler = attach_log_handler(provider)
    try:
        logging.getLogger("custom_components.opentelemetry.metrics").info("hello")
    finally:
        detach_log_handler(handler)

    logs = exporter.get_finished_logs()
    assert len(logs) == 1
    assert logs[0].log_record.attributes["homeassistant.domain"] == "opentelemetry"


def test_unrelated_logger_gets_no_domain_attribute() -> None:
    """A logger outside the known naming conventions gets no domain attribute."""
    provider, exporter = _provider_with_exporter()
    handler = attach_log_handler(provider)
    try:
        logging.getLogger("asyncio").info("hello")
    finally:
        detach_log_handler(handler)

    logs = exporter.get_finished_logs()
    assert len(logs) == 1
    assert "homeassistant.domain" not in logs[0].log_record.attributes


def test_own_otel_logs_are_excluded() -> None:
    """Logs from the OTel SDK itself are dropped to avoid a feedback loop."""
    provider, exporter = _provider_with_exporter()
    handler = attach_log_handler(provider)
    try:
        logging.getLogger("opentelemetry.exporter.otlp.proto.grpc").error("boom")
    finally:
        detach_log_handler(handler)

    assert exporter.get_finished_logs() == ()
