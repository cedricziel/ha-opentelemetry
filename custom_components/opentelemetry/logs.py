"""Log forwarding for the OpenTelemetry integration."""
from __future__ import annotations

import logging
import re

from opentelemetry._logs import LoggerProvider
from opentelemetry.instrumentation.logging.handler import LoggingHandler

_DOMAIN_RE = re.compile(
    r"^(?:homeassistant\.components|custom_components)\.([A-Za-z0-9_]+)"
)


class _DomainFilter(logging.Filter):
    """Attaches the integration domain derived from the logger name."""

    def filter(self, record: logging.LogRecord) -> bool:
        match = _DOMAIN_RE.match(record.name)
        if match:
            setattr(record, "homeassistant.domain", match.group(1))
        return True


class _ExcludeOwnLogsFilter(logging.Filter):
    """Drops the OTel SDK's own logs, avoiding an export-failure feedback loop."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith("opentelemetry")


def attach_log_handler(
    provider: LoggerProvider, level: int = logging.INFO
) -> LoggingHandler:
    """Attach an OTLP logging handler to the Home Assistant root logger."""
    handler = LoggingHandler(level=level, logger_provider=provider)
    handler.addFilter(_ExcludeOwnLogsFilter())
    handler.addFilter(_DomainFilter())
    logging.getLogger().addHandler(handler)
    return handler


def detach_log_handler(handler: LoggingHandler) -> None:
    """Detach and close a previously attached logging handler."""
    logging.getLogger().removeHandler(handler)
    handler.close()
