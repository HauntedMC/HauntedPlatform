# HauntedPlatform

HauntedPlatform is HauntedMC's shared **external dependency and build policy**. It contains no gameplay or runtime code. A Platform release changes Paper and Velocity APIs and runtime checksums, third-party library versions, Maven plugin versions, Java/tooling rules, or shared parent behavior. It does not select versions of HauntedMC libraries.

| Artifact | Purpose |
| --- | --- |
| `haunted-parent` | Java 25, Maven plugins, Enforcer, Checkstyle, coverage, flattening, deployment policy |
| `haunted-library-parent` | Parent for reusable libraries; imports the third-party BOM |
| `haunted-application-parent` | Parent for applications; imports both third-party and Minecraft BOMs |
| `haunted-dependencies-bom` | Platform-neutral third-party versions such as OpenTelemetry, Adventure, Gson, SLF4J, Hibernate, and test libraries |
| `haunted-minecraft-bom` | Paper, Velocity, Brigadier, PlaceholderAPI, ViaVersion, and other Minecraft integration APIs |
| `haunted-build-rules` | Shared Checkstyle configuration |

Internal versions belong to the consuming repository. DataProvider, DataRegistry, FeatureFramework, and HauntedObservability publish BOMs for **their own** modules. Theme publishes palette and FeatureFramework adapter separately. ProxyFeatures and ServerFeatures import those BOMs and select each released internal version in their root POMs. Dungeons, VelocityHotReloader, PaperHotReloader, AIlex, and CraftGPT inherit the application parent for build and Minecraft dependency policy without adding runtime HauntedMC library dependencies. This removes the former `haunted-platform-bom` release cycle; version 1.6.10 remains available for older consumers, but 2.0.0 and later do not publish that artifact.

## Maven consumption

GitHub Packages requires authenticated Maven access. All HauntedMC builds use Maven server id `github` and set `PACKAGES_USER` and `PACKAGES_TOKEN` in CI or the local environment. Their committed `.mvn/settings.xml` and `.mvn/maven.config` make the package repository available before Maven resolves a parent POM. Never commit package credentials.

Reusable libraries inherit `nl.hauntedmc.platform:haunted-library-parent:2.0.0`. Applications inherit `nl.hauntedmc.platform:haunted-application-parent:2.0.0`. Projects that cannot inherit a parent can import `haunted-dependencies-bom` directly; applications can also import `haunted-minecraft-bom`. Keep external dependency and Maven plugin versions in Platform, and keep application-specific shading, acceptance fixtures, and compatibility choices in their owning repositories.

A consuming project's root POM chooses its internal versions explicitly:

```xml
<properties>
  <haunted.dataprovider.version>3.4.4</haunted.dataprovider.version>
  <haunted.dataregistry.version>1.18.5</haunted.dataregistry.version>
</properties>
<dependencyManagement><dependencies>
  <dependency>
    <groupId>nl.hauntedmc.dataprovider</groupId>
    <artifactId>dataprovider-bom</artifactId>
    <version>${haunted.dataprovider.version}</version>
    <type>pom</type><scope>import</scope>
  </dependency>
  <dependency>
    <groupId>nl.hauntedmc.dataregistry</groupId>
    <artifactId>dataregistry-bom</artifactId>
    <version>${haunted.dataregistry.version}</version>
    <type>pom</type><scope>import</scope>
  </dependency>
</dependencies></dependencyManagement>
```

The version examples above become usable only after their corresponding releases have been published. Do not point a PR at an unpublished package. Each root property is a compatibility decision for that consumer; updating one does not require another Platform release.

Maven Dependabot runs in HauntedPlatform only. Downstream repositories retain GitHub Actions Dependabot updates; their Maven updates come from a reviewed Platform release or the internal release reconciler. Consumer CI rejects literal external dependency/plugin versions and local overrides of Platform-owned version properties.

## Releasing and downstream updates

A reviewed version bump merged into `main` triggers the repository's release workflow. It runs the full owner-specific quality gate, deploys with `deployAtEnd`, resolves every published artifact from a fresh Maven cache, and only then creates the immutable release tag. A GitHub App dispatches a reconciliation workflow here, which opens or refreshes reviewed downstream PRs in dependency order. Each consumer's CI and release workflow remain its own gate. A failed publication leaves no new tag; rerun the release workflow after fixing the failure. Existing tags are never moved.

See [the release and rollout guide](docs/releasing.md) for the graph, GitHub App setup, bootstrap order, and recovery procedure. Contributions are welcome under [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md); report vulnerabilities privately through [SECURITY.md](SECURITY.md). The project is licensed under [AGPL-3.0](LICENSE).
