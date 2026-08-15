"""The OpenTelemetry integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import instance_id

from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .const import (
    CONF_AUTH_HEADER,
    CONF_DATASET_ID,
    CONF_ENABLE_LOGS,
    CONF_ENABLE_METRICS,
    CONF_ENABLE_TRACES,
    CONF_ENDPOINT,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_DOMAINS,
    CONF_INSECURE,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SCOPE_ENTITIES,
    CONF_SCOPE_SYSTEM,
    CONF_SERVICE_NAME,
    CONF_TENANT_ID,
    DEFAULT_ENABLE_LOGS,
    DEFAULT_ENABLE_METRICS,
    DEFAULT_ENABLE_TRACES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCOPE_ENTITIES,
    DEFAULT_SCOPE_SYSTEM,
    DOMAIN,
    PROTOCOL_GRPC,
)
from .logs import attach_log_handler, detach_log_handler
from .metrics import HomeAssistantMetrics
from .traces import HomeAssistantTracing

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []


def _headers(entry: ConfigEntry) -> dict[str, str]:
    headers: dict[str, str] = {"x-tenant-id": entry.data[CONF_TENANT_ID]}
    auth_header = entry.data.get(CONF_AUTH_HEADER)
    if auth_header:
        headers["authorization"] = auth_header
    dataset_id = entry.data.get(CONF_DATASET_ID)
    if dataset_id:
        headers["x-dataset-id"] = dataset_id
    return headers


def _grpc_endpoint(endpoint: str) -> str:
    return endpoint.removeprefix("https://").removeprefix("http://")


def _http_endpoint(endpoint: str, path: str) -> str:
    base = endpoint if endpoint.startswith("http") else f"http://{endpoint}"
    return f"{base.rstrip('/')}{path}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenTelemetry exporters from a config entry."""
    data = entry.data
    options = entry.options

    endpoint = data[CONF_ENDPOINT]
    protocol = data.get(CONF_PROTOCOL, PROTOCOL_GRPC)
    insecure = data.get(CONF_INSECURE, True)
    headers = _headers(entry)

    enable_traces = options.get(CONF_ENABLE_TRACES, DEFAULT_ENABLE_TRACES)
    enable_metrics = options.get(CONF_ENABLE_METRICS, DEFAULT_ENABLE_METRICS)
    enable_logs = options.get(CONF_ENABLE_LOGS, DEFAULT_ENABLE_LOGS)
    scope_system = options.get(CONF_SCOPE_SYSTEM, DEFAULT_SCOPE_SYSTEM)
    scope_entities = options.get(CONF_SCOPE_ENTITIES, DEFAULT_SCOPE_ENTITIES)
    scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    include_domains = options.get(CONF_INCLUDE_DOMAINS, [])
    exclude_entities = options.get(CONF_EXCLUDE_ENTITIES, [])

    ha_uuid = await instance_id.async_get(hass)
    resource = Resource.create(
        {
            "service.name": data.get(CONF_SERVICE_NAME, DOMAIN),
            "service.namespace": "homeassistant",
            "service.instance.id": ha_uuid,
        }
    )

    runtime: dict = {}

    if enable_traces:
        if protocol == PROTOCOL_GRPC:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            span_exporter = OTLPSpanExporter(
                endpoint=_grpc_endpoint(endpoint), headers=headers, insecure=insecure
            )
        else:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            span_exporter = OTLPSpanExporter(
                endpoint=_http_endpoint(endpoint, "/v1/traces"), headers=headers
            )
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        tracer = tracer_provider.get_tracer(DOMAIN)
        runtime["tracer_provider"] = tracer_provider
        runtime["tracing"] = HomeAssistantTracing(
            hass, tracer, scope_system=scope_system, scope_entities=scope_entities
        )

    if enable_metrics:
        if protocol == PROTOCOL_GRPC:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )

            metric_exporter = OTLPMetricExporter(
                endpoint=_grpc_endpoint(endpoint), headers=headers, insecure=insecure
            )
        else:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                OTLPMetricExporter,
            )

            metric_exporter = OTLPMetricExporter(
                endpoint=_http_endpoint(endpoint, "/v1/metrics"), headers=headers
            )
        reader = PeriodicExportingMetricReader(
            metric_exporter, export_interval_millis=scan_interval * 1000
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        meter = meter_provider.get_meter(DOMAIN)
        runtime["meter_provider"] = meter_provider
        runtime["metrics"] = HomeAssistantMetrics(
            hass,
            meter,
            scope_system=scope_system,
            scope_entities=scope_entities,
            include_domains=include_domains,
            exclude_entities=exclude_entities,
        )

    if enable_logs:
        if protocol == PROTOCOL_GRPC:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
                OTLPLogExporter,
            )

            log_exporter = OTLPLogExporter(
                endpoint=_grpc_endpoint(endpoint), headers=headers, insecure=insecure
            )
        else:
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (
                OTLPLogExporter,
            )

            log_exporter = OTLPLogExporter(
                endpoint=_http_endpoint(endpoint, "/v1/logs"), headers=headers
            )
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(log_exporter)
        )
        runtime["logger_provider"] = logger_provider
        runtime["log_handler"] = attach_log_handler(logger_provider)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entry and shut down all providers cleanly."""
    runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime is None:
        return True

    tracing: HomeAssistantTracing | None = runtime.get("tracing")
    if tracing is not None:
        tracing.async_shutdown()

    metrics: HomeAssistantMetrics | None = runtime.get("metrics")
    if metrics is not None:
        metrics.async_shutdown()

    log_handler = runtime.get("log_handler")
    if log_handler is not None:
        detach_log_handler(log_handler)

    for key in ("tracer_provider", "meter_provider", "logger_provider"):
        provider = runtime.get(key)
        if provider is not None:
            await hass.async_add_executor_job(provider.shutdown)

    return True
