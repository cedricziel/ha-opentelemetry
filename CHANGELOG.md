# Changelog

## [0.4.0](https://github.com/cedricziel/ha-opentelemetry/compare/v0.3.1...v0.4.0) (2026-08-15)


### Features

* **opentelemetry:** add entity/device/area registry resolution helper ([9eaef11](https://github.com/cedricziel/ha-opentelemetry/commit/9eaef11b8e401537ed52f3c2ca69443ceabdb874))
* **opentelemetry:** correlate spans via event context, add automation spans, gate state-changed spans ([ab33a7e](https://github.com/cedricziel/ha-opentelemetry/commit/ab33a7e238acf42bef4f909e6858f623bcf1f2db))
* **opentelemetry:** enrich forwarded logs with domain, exclude OTel's own logs ([7ce0fdb](https://github.com/cedricziel/ha-opentelemetry/commit/7ce0fdb19f3c4737ee9802a51e57616367e8f1c0))
* **opentelemetry:** redesign system metrics as event throughput, health, and setup timing ([b52de65](https://github.com/cedricziel/ha-opentelemetry/commit/b52de6510bfb4fe8bff786478bad3b0d2a0f59ca))

## [0.3.1](https://github.com/cedricziel/ha-opentelemetry/compare/v0.3.0...v0.3.1) (2026-08-15)


### Bug Fixes

* **opentelemetry:** fix crashing process/host metric callbacks ([175fba0](https://github.com/cedricziel/ha-opentelemetry/commit/175fba0af95a34f3466a5ef1fd9e241f562b42ec))

## [0.3.0](https://github.com/cedricziel/ha-opentelemetry/compare/v0.2.0...v0.3.0) (2026-08-15)


### Features

* **opentelemetry:** collect process and host resource metrics ([480b145](https://github.com/cedricziel/ha-opentelemetry/commit/480b145798f34ffb893d2265dcbe5deba347b25d))

## [0.2.0](https://github.com/cedricziel/ha-opentelemetry/compare/v0.1.0...v0.2.0) (2026-08-15)


### Features

* **opentelemetry:** add reconfigure flow for connection settings ([c332f45](https://github.com/cedricziel/ha-opentelemetry/commit/c332f458d712b0d7e3655367ca2992d1a8a7202e))


### Bug Fixes

* **ci:** drop unused zip asset from releases ([9c9a8fc](https://github.com/cedricziel/ha-opentelemetry/commit/9c9a8fcf9def386927dbf96521e2ea7aaa894aa7))
