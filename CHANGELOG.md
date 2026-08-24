# Changelog

## 1.2.0

- Upgraded the shared Checkstyle engine to 14.0.0.
- Added isolated-install external-consumer verification before Platform deployment and retained fresh-repository post-deployment verification.
- Centralized shared Testcontainers, SnakeYAML, duplicate-finder, and application SBOM-plugin versions without changing local runtime or plugin behavior.

## Release policy

Platform versions and workflow tags are immutable. Upgrade consumers only to a published Platform release. The ecosystem BOM is updated only after the public foundation artifacts it names have been released.
