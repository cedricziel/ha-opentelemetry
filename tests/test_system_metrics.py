"""Tests for process/host resource metric instrumentation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from opentelemetry.instrumentation.system_metrics import _build_default_config
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from custom_components.opentelemetry.system_metrics import (
    HOST_METRICS,
    PROCESS_METRICS,
    start_system_metrics,
    stop_system_metrics,
)


def test_start_system_metrics_both_enabled() -> None:
    """Both process and host metric names are passed when both are enabled."""
    meter_provider = MagicMock()
    with patch(
        "custom_components.opentelemetry.system_metrics.SystemMetricsInstrumentor"
    ) as mock_cls:
        instrumentor = mock_cls.return_value
        result = start_system_metrics(
            meter_provider, process_metrics=True, host_metrics=True
        )

    config = mock_cls.call_args.kwargs["config"]
    assert set(config) == set(PROCESS_METRICS) | set(HOST_METRICS)
    instrumentor.instrument.assert_called_once_with(meter_provider=meter_provider)
    assert result is instrumentor


def test_config_values_match_real_defaults() -> None:
    """The config passed for each selected key must be the instrumentor's
    real default value for that key (a sub-metric list, or None only where
    the metric genuinely takes none) — not a synthesized placeholder.

    A shipped version passed None for every key regardless of what the
    instrumentor actually expected there, which crashed every callback
    with 'NoneType is not iterable' as soon as a collection cycle ran.
    """
    real_defaults = _build_default_config()
    with patch(
        "custom_components.opentelemetry.system_metrics.SystemMetricsInstrumentor"
    ) as mock_cls:
        start_system_metrics(MagicMock(), process_metrics=True, host_metrics=True)

    config = mock_cls.call_args.kwargs["config"]
    for name in PROCESS_METRICS + HOST_METRICS:
        assert config[name] == real_defaults[name]


def test_start_system_metrics_process_only() -> None:
    """Only process metric names are passed when host metrics are disabled."""
    meter_provider = MagicMock()
    with patch(
        "custom_components.opentelemetry.system_metrics.SystemMetricsInstrumentor"
    ) as mock_cls:
        start_system_metrics(meter_provider, process_metrics=True, host_metrics=False)

    config = mock_cls.call_args.kwargs["config"]
    assert set(config) == set(PROCESS_METRICS)


def test_start_system_metrics_none_enabled_returns_none() -> None:
    """No instrumentor is created when both are disabled."""
    meter_provider = MagicMock()
    with patch(
        "custom_components.opentelemetry.system_metrics.SystemMetricsInstrumentor"
    ) as mock_cls:
        result = start_system_metrics(
            meter_provider, process_metrics=False, host_metrics=False
        )

    mock_cls.assert_not_called()
    assert result is None


def test_stop_system_metrics_uninstruments() -> None:
    """stop_system_metrics calls uninstrument on the instrumentor."""
    instrumentor = MagicMock()
    stop_system_metrics(instrumentor)
    instrumentor.uninstrument.assert_called_once_with()


def test_collection_cycle_does_not_log_callback_errors(caplog) -> None:
    """End to end against the real instrumentor: a collection cycle must not
    log any "Callback failed" errors. The OTel SDK logs-and-swallows
    exceptions raised inside observable-instrument callbacks rather than
    propagating them, so asserting "it didn't raise" alone would not have
    caught the regression this guards against.
    """
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    instrumentor = start_system_metrics(
        provider, process_metrics=True, host_metrics=True
    )
    try:
        with caplog.at_level("ERROR"):
            data = reader.get_metrics_data()
        collected_names = {
            metric.name
            for rm in data.resource_metrics
            for sm in rm.scope_metrics
            for metric in sm.metrics
        }
        assert collected_names
        assert "Callback failed" not in caplog.text
    finally:
        stop_system_metrics(instrumentor)
