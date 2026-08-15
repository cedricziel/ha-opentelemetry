"""Process and host resource metrics for the OpenTelemetry integration.

Wraps the official ``opentelemetry-instrumentation-system-metrics``
package, which reads these via ``psutil``. Process metrics describe the
Home Assistant Python process itself (CPU, memory, threads, GC); host
metrics describe the machine/container Home Assistant runs on (CPU,
memory, swap, disk, network). Both use standard OpenTelemetry semantic
conventions (``process.*``, ``cpython.*``, ``system.*``) rather than
integration-specific names.
"""
from __future__ import annotations

from opentelemetry.instrumentation.system_metrics import (
    SystemMetricsInstrumentor,
    _build_default_config,
)
from opentelemetry.sdk.metrics import MeterProvider

PROCESS_METRICS = [
    "process.context_switches",
    "process.cpu.time",
    "process.cpu.utilization",
    "process.memory.usage",
    "process.memory.virtual",
    "process.open_file_descriptor.count",
    "process.thread.count",
    "process.disk.io",
    "process.runtime.memory",
    "process.runtime.cpu.time",
    "process.runtime.gc_count",
    "cpython.gc.collections",
    "cpython.gc.collected_objects",
    "cpython.gc.uncollectable_objects",
    "process.runtime.thread_count",
    "process.runtime.cpu.utilization",
    "process.runtime.context_switches",
]

HOST_METRICS = [
    "system.cpu.time",
    "system.cpu.utilization",
    "system.memory.usage",
    "system.memory.utilization",
    "system.swap.usage",
    "system.swap.utilization",
    "system.disk.io",
    "system.disk.operations",
    "system.disk.time",
    "system.network.dropped.packets",
    "system.network.packets",
    "system.network.errors",
    "system.network.io",
    "system.thread_count",
]


def start_system_metrics(
    meter_provider: MeterProvider,
    *,
    process_metrics: bool,
    host_metrics: bool,
) -> SystemMetricsInstrumentor | None:
    """Instrument the enabled process/host metric names, if any."""
    names = [*(PROCESS_METRICS if process_metrics else [])]
    names += HOST_METRICS if host_metrics else []
    if not names:
        return None

    defaults = _build_default_config()
    config = {name: defaults[name] for name in names}
    instrumentor = SystemMetricsInstrumentor(config=config)
    instrumentor.instrument(meter_provider=meter_provider)
    return instrumentor


def stop_system_metrics(instrumentor: SystemMetricsInstrumentor) -> None:
    """Uninstrument process/host metrics."""
    instrumentor.uninstrument()
