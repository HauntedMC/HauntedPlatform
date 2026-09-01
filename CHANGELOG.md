# Changelog

## 1.5.0

- Updated the ecosystem BOM to FeatureFramework 1.8.0, DataProvider 3.4.1, and DataRegistry 1.16.0 for the clean-break multi-proxy release.
- Kept the library and application parents as the supported entry points, so application projects inherit the aligned foundation catalog without local overrides.

## 1.4.0

- Finalized the observability-capable HauntedMC ecosystem baseline.
- Updated FeatureFramework to 1.7.0, DataProvider to 3.3.0, and DataRegistry to 1.15.0.
- Added HauntedObservability 1.0.0 through its published BOM so application consumers can use its modules without local version pins.
- Extended application consumer and Paper/Velocity regression fixtures to verify the aligned HauntedObservability dependency graph together with FeatureFramework, DataProvider, and DataRegistry.
- Kept Java 25, OpenTelemetry 1.65.0, runtime telemetry 2.31.0-alpha, and unrelated build/runtime policy unchanged.

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
