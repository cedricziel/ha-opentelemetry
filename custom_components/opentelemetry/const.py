"""Constants for the OpenTelemetry integration."""
from __future__ import annotations

DOMAIN = "opentelemetry"

CONF_ENDPOINT = "endpoint"
CONF_PROTOCOL = "protocol"
CONF_INSECURE = "insecure"
CONF_AUTH_HEADER = "auth_header"
CONF_TENANT_ID = "tenant_id"
CONF_DATASET_ID = "dataset_id"
CONF_SERVICE_NAME = "service_name"

PROTOCOL_GRPC = "grpc"
PROTOCOL_HTTP = "http"
PROTOCOLS = [PROTOCOL_GRPC, PROTOCOL_HTTP]

DEFAULT_SERVICE_NAME = "homeassistant"
DEFAULT_PROTOCOL = PROTOCOL_GRPC
DEFAULT_INSECURE = True

# Options
CONF_ENABLE_TRACES = "enable_traces"
CONF_ENABLE_METRICS = "enable_metrics"
CONF_ENABLE_LOGS = "enable_logs"
CONF_SCOPE_SYSTEM = "scope_system"
CONF_SCOPE_ENTITIES = "scope_entities"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_INCLUDE_DOMAINS = "include_domains"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_ENABLE_PROCESS_METRICS = "enable_process_metrics"
CONF_ENABLE_HOST_METRICS = "enable_host_metrics"

DEFAULT_ENABLE_TRACES = True
DEFAULT_ENABLE_METRICS = True
DEFAULT_ENABLE_LOGS = True
DEFAULT_SCOPE_SYSTEM = True
DEFAULT_SCOPE_ENTITIES = True
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_ENABLE_PROCESS_METRICS = True
DEFAULT_ENABLE_HOST_METRICS = True

MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600
