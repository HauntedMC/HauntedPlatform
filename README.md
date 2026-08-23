# HauntedPlatform

HauntedPlatform is the public Maven build and dependency-management standard for HauntedMC Java software. It contains no Minecraft runtime or gameplay code.

| Artifact | Use |
| --- | --- |
| `haunted-parent` | Java 25, Maven plugin policy, Enforcer, shared Checkstyle, generic JaCoCo, flattening and deployment policy. |
| `haunted-library-parent` | Parent for independently reusable libraries; imports only `haunted-dependencies-bom`. |
| `haunted-application-parent` | Parent for HauntedMC applications; imports `haunted-platform-bom`. |
| `haunted-dependencies-bom` | Platform-neutral third-party versions. |
| `haunted-platform-bom` | Validated public HauntedMC foundation-library versions and FeatureFramework's own BOM. |
| `haunted-build-rules` | Packaged Checkstyle configuration consumed by the shared parent. |

`FeatureFramework`, `DataProvider`, and `DataRegistry` use `haunted-library-parent`. `ServerFeatures` and `ProxyFeatures` use `haunted-application-parent`. Platform-specific APIs, shading, acceptance tests, repositories, SCM data, release destinations, and coverage thresholds stay in their owning repositories.

## Publishing

Releases publish to Maven Central through the Central Portal, not GitHub Packages. The release workflow expects these GitHub Actions secrets: `CENTRAL_USERNAME`, `CENTRAL_PASSWORD`, `MAVEN_GPG_PRIVATE_KEY`, and `MAVEN_GPG_PASSPHRASE`.

Before the first release, a HauntedMC maintainer must verify the `nl.hauntedmc.platform` namespace in Central Portal, create a deployment token, and add those secrets. `haunted-platform-bom` imports public foundation artifacts, so their referenced release versions must also be available from Maven Central before publishing this BOM. This repository deliberately does not fall back to GitHub-Packages-only consumption.

## Verification

`verification` builds three external-style fixtures using installed artifacts and `<relativePath/>`: a plain BOM consumer, a library-parent consumer, and an application-parent consumer. Run `mvn clean install`, then `mvn -f verification/bom-consumer/pom.xml verify`, and the equivalent commands for the two parent fixtures with a fresh local repository when validating a release candidate.
