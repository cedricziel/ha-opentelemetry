# OpenTelemetry for Home Assistant

[![Validate](https://github.com/cedricziel/ha-opentelemetry/actions/workflows/validate.yml/badge.svg)](https://github.com/cedricziel/ha-opentelemetry/actions/workflows/validate.yml)
[![Test](https://github.com/cedricziel/ha-opentelemetry/actions/workflows/test.yml/badge.svg)](https://github.com/cedricziel/ha-opentelemetry/actions/workflows/test.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A [HACS](https://hacs.xyz/) custom integration that exports Home Assistant telemetry — metrics, logs, and traces — to any [OpenTelemetry](https://opentelemetry.io/) (OTLP) backend: an OpenTelemetry Collector, Grafana Tempo/Loki/Mimir, or a database like [SignalDB](https://github.com/cedricziel/signaldb).

Only the current Home Assistant release is supported — no back-compat testing against older cores. `hacs.json` pins the minimum HA version to the current release line, and CI always tests against the latest `pytest-homeassistant-custom-component`.

## What it exports

Each signal can be turned on or off independently, and scoped to system-level telemetry, per-entity telemetry, or both:

| Signal  | System scope | Entity scope |
| ------- | --- | --- |
| **Metrics** | Bus events by type (`homeassistant.events`), entity counts by domain, unavailable-entity counts by domain, config-entry counts by domain/state, per-domain setup duration | Numeric entity state as a gauge, with `homeassistant.entity_id`, `homeassistant.domain`, `homeassistant.unit`, `homeassistant.area` attributes |
| **Logs** | Home Assistant's own log records, forwarded via the standard `logging` bridge, enriched with `homeassistant.domain` derived from the logger name | — |
| **Traces** | A point-in-time span per service call (`service_call <domain>.<service>`) and per automation trigger (`automation_triggered <entity_id>`) | Entity ID/area attached to service-call spans; state-changed spans (`state_changed <entity_id>`), off by default — see below |

Traces are point-in-time (`start_time == end_time`): Home Assistant exposes no public hook around service-call or automation-run completion, so these mark that something happened rather than covering its execution duration. Every span carries `homeassistant.context.id`/`.parent_id`/`.user_id` from the originating Home Assistant event context, so a backend can join an automation trigger to the service calls it caused.

State-changed spans are **off by default** — a busy home can produce hundreds of thousands a day, they carry no duration, and the same information is already available as the `homeassistant.entity.state` metric. Turn them on via the `enable_state_changed_traces` option if you specifically want per-change spans (e.g. for automation debugging); they respect the same entity include/exclude filters as entity-scoped metrics.

Two more metric groups are independently toggleable, using standard OTel semantic conventions (not `homeassistant.*`) via the official [`opentelemetry-instrumentation-system-metrics`](https://pypi.org/project/opentelemetry-instrumentation-system-metrics/) package:

- **Process metrics** (`process.*`, `cpython.*`): the Home Assistant Python process's own CPU, memory, threads, file descriptors, and GC stats.
- **Host metrics** (`system.*`): CPU, memory, swap, disk, and network of the machine/container Home Assistant runs on. In a containerized install (e.g. Home Assistant OS), these reflect what's visible from inside that container.

### Semantic conventions

The exact attribute, metric, and span names above are formally defined as an [OpenTelemetry Weaver](https://github.com/open-telemetry/weaver) semantic-convention registry in [`weaver/`](weaver/), extending the standard OTel semantic conventions. Validate it with:

```console
weaver registry check -r weaver
```

CI runs this on every change to `weaver/`.

## Installation

1. In HACS, add this repository as a custom repository (category: Integration): `https://github.com/cedricziel/ha-opentelemetry`.
2. Install "OpenTelemetry" and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → OpenTelemetry**.
4. Enter your OTLP endpoint, protocol (gRPC or HTTP), and auth headers.
5. Open the integration's **Configure** button to choose which signals and scopes to export, and the metric export interval.

## Configuration

### Connection (set once, at setup)

| Field | Description |
| --- | --- |
| Endpoint | `host:port` for gRPC (e.g. `192.168.178.6:4317`), or a base URL for HTTP (e.g. `http://192.168.178.6:4318`) |
| Protocol | `grpc` or `http` |
| Insecure | Plaintext connection (no TLS) — typical for a collector on the local network |
| Authorization header | Full header value, e.g. `Bearer sk-...` |
| Tenant ID | Sent as `x-tenant-id` on every request |
| Dataset ID | Optional, sent as `x-dataset-id` |
| Service name | Reported as the `service.name` resource attribute |

### Options (changeable any time, reload on save)

Enable/disable traces, metrics, logs; include system-level and/or per-entity telemetry; include process and/or host resource metrics; opt in to state-changed trace spans; set the metric export interval; and optionally restrict per-entity telemetry (metrics and, if enabled, state-changed spans) to specific domains or exclude specific entities.

## Development

```console
pip install -r requirements-test.txt
pytest
ruff check custom_components tests
```

## License

MIT — see [LICENSE](LICENSE).

The icon in [`custom_components/opentelemetry/brand/`](custom_components/opentelemetry/brand/) is the official [OpenTelemetry](https://opentelemetry.io/) logo, from [cncf/artwork](https://github.com/cncf/artwork/tree/master/projects/opentelemetry), used per the [CNCF trademark usage guidelines](https://github.com/cncf/artwork/blob/master/LICENSE.md) to indicate OTLP compatibility.
