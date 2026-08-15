"""Log forwarding for the OpenTelemetry integration."""
from __future__ import annotations

import logging

from opentelemetry._logs import LoggerProvider
from opentelemetry.instrumentation.logging.handler import LoggingHandler


def attach_log_handler(
    provider: LoggerProvider, level: int = logging.INFO
) -> LoggingHandler:
    """Attach an OTLP logging handler to the Home Assistant root logger."""
    handler = LoggingHandler(level=level, logger_provider=provider)
    logging.getLogger().addHandler(handler)
    return handler


def detach_log_handler(handler: LoggingHandler) -> None:
    """Detach and close a previously attached logging handler."""
    logging.getLogger().removeHandler(handler)
    handler.close()
