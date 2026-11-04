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

Internal versions belong to the consuming repository. DataProvider, DataRegistry, FeatureFramework, and HauntedObservability publish BOMs for **their own** modules. Theme publishes palette and FeatureFramework adapter separately. ProxyFeatures and ServerFeatures import those BOMs and select each released internal version in their root POMs. Dungeons, VelocityHotReloader, PaperHotReloader, AIlex, CraftGPT, WebApp, and HauntedControlPlane inherit the application parent for build policy without adding runtime HauntedMC library dependencies. This removes the former `haunted-platform-bom` release cycle; version 1.6.10 remains available for older consumers, but 2.0.0 and later do not publish that artifact.

Platform 2.1.0 targets Paper `26.3.build.241-stable` (runtime build 241), Velocity `4.3.1` (runtime build 45), and MockBukkit `mockbukkit-v26.3:4.119.0`. Java 25 remains the shared build target.

The Minecraft integration pins were audited for this release:

| Integration | Managed version |
| --- | --- |
| PacketEvents | 2.14.0 |
| Citizens | 2.0.44-SNAPSHOT (upstream publishes snapshots) |
| ViaVersion | 5.12.2 |
| LibsDisguises | 26.10.24 |
| WorldGuard / WorldEdit | 7.0.21 / 7.4.6 |
| FastAsyncWorldEdit | 2.16.2 |
| Item-NBT-API | 2.16.1 (already includes 26.3 support) |
| PlaceholderAPI / LuckPerms API / Vault API | 2.12.3 / 5.5 / 1.7.1 (current published APIs) |
| GriefPrevention | 18.0.0 (current published Maven coordinate) |
| EssentialsX | 2.21.2 (2.22.0 release exists, but its Maven artifact is not published) |

Consumers that import internal BOMs in their own dependency management must import
`haunted-dependencies-bom` (and `haunted-minecraft-bom` for applications) first, using
`${haunted.platform.version}`. Otherwise Maven can prefer an older external version
inherited by an internal BOM over the selected parent.

CI and release verification resolve every managed Minecraft integration JAR through
`verification/minecraft-bom-consumer`. This checks coordinate availability; each plugin's
own tests and runtime acceptance checks establish compatibility. Publish Platform before
merging downstream parent updates so their builds can resolve 2.1.0.

## Maven consumption

GitHub Packages requires authenticated Maven access. All HauntedMC builds use Maven server id `github` and set `PACKAGES_USER` and `PACKAGES_TOKEN` in CI or the local environment. Their committed `.mvn/settings.xml` and `.mvn/maven.config` make the package repository available before Maven resolves a parent POM. Never commit package credentials.

Reusable libraries inherit `nl.hauntedmc.platform:haunted-library-parent:2.1.0`. Applications inherit `nl.hauntedmc.platform:haunted-application-parent:2.1.0`. Projects that cannot inherit a parent can import `haunted-dependencies-bom` directly; applications can also import `haunted-minecraft-bom`. Keep external dependency and Maven plugin versions in Platform, and keep application-specific shading, acceptance fixtures, and compatibility choices in their owning repositories.

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

Maven Dependabot runs in HauntedPlatform only. Most downstream repositories retain GitHub Actions Dependabot updates; their Maven parent updates come from a reviewed Platform release or the internal release reconciler. WebApp manages its Spring Boot application BOM separately. WebApp, HauntedControlPlane, ProxyFeatures, and ServerFeatures verify reviewed updates locally while Actions are disabled. Enabled consumer CI rejects literal external dependency/plugin versions and local overrides of Platform-owned version properties.

## Releasing and downstream updates

A reviewed version bump merged into `main` triggers the repository's release workflow. It runs the full owner-specific quality gate, deploys with `deployAtEnd`, resolves every published artifact from a fresh Maven cache, and only then creates the immutable release tag. A GitHub App dispatches a reconciliation workflow here, which opens or refreshes reviewed downstream PRs in dependency order. Each consumer's CI and release workflow remain its own gate. A failed publication leaves no new tag; rerun the release workflow after fixing the failure. Existing tags are never moved.

See [the release and rollout guide](docs/releasing.md) for the graph, GitHub App setup, bootstrap order, and recovery procedure. Contributions are welcome under [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md); report vulnerabilities privately through [SECURITY.md](SECURITY.md). The project is licensed under [AGPL-3.0](LICENSE).
