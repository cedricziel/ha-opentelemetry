"""Tests for process/host resource metric instrumentation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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
