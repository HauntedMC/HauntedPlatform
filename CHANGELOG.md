# Changelog

## 1.3.0

- Added OpenTelemetry 1.65.0 dependency management through the official stable OpenTelemetry BOM.
- Added managed unified JVM runtime telemetry `2.31.0-alpha`, aligned with OpenTelemetry 1.65.0.
- Updated external consumer verification so both library and application parents prove the OpenTelemetry API, SDK/exporter, and runtime-telemetry versions resolve without local pins.

## 1.2.0

- Upgraded the shared Checkstyle engine to 14.0.0.
- Added isolated-install external-consumer verification before Platform deployment and retained fresh-repository post-deployment verification.
- Centralized shared Testcontainers, SnakeYAML, duplicate-finder, and application SBOM-plugin versions without changing local runtime or plugin behavior.

## Release policy

Platform versions and workflow tags are immutable. Upgrade consumers only to a published Platform release. The ecosystem BOM is updated only after the public foundation artifacts it names have been released.
