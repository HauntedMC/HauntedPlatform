# HauntedPlatform

HauntedPlatform is the Java build and dependency-management standard for HauntedMC software. It contains no Minecraft runtime or gameplay code.

| Artifact | Intended use |
| --- | --- |
| `haunted-parent` | Java 25, plugin policy, Enforcer, Checkstyle, generic JaCoCo, flattening, and deployment policy. |
| `haunted-library-parent` | Parent for reusable libraries; imports only `haunted-dependencies-bom`. |
| `haunted-application-parent` | Parent for deployable HauntedMC applications; imports `haunted-platform-bom`. |
| `haunted-dependencies-bom` | Shared platform-neutral third-party versions, including OpenTelemetry, Hibernate, and other dependencies shared across projects. |
| `haunted-platform-bom` | Validated public HauntedMC foundation-library versions, including FeatureFramework and HauntedObservability through their published BOMs plus all regular DataProvider/DataRegistry/Theme modules. |
| `haunted-build-rules` | Packaged Checkstyle configuration consumed by the shared parent. |

FeatureFramework, DataProvider, DataRegistry, HauntedObservability, and Theme use `haunted-library-parent`. ServerFeatures and ProxyFeatures use `haunted-application-parent`. Runtime targets, shading, acceptance tests, project metadata, release locations, and coverage thresholds remain in their owning repositories.

## Maven consumption

HauntedPlatform is published only to GitHub Packages. GitHub requires authentication for Maven package downloads, including public packages. Supply a classic personal access token with `read:packages` (and repository access where required) through environment variables; never commit a token.

```xml
<settings>
  <servers>
    <server>
      <id>github</id>
      <username>${env.PACKAGES_USER}</username>
      <password>${env.PACKAGES_TOKEN}</password>
    </server>
  </servers>
  <profiles><profile><id>hauntedmc</id><repositories>
    <repository><id>central</id><url>https://repo.maven.apache.org/maven2</url></repository>
    <repository><id>github</id><url>https://maven.pkg.github.com/hauntedmc/*</url></repository>
  </repositories>
  <pluginRepositories><pluginRepository><id>github</id><url>https://maven.pkg.github.com/hauntedmc/*</url></pluginRepository></pluginRepositories>
  </profile></profiles>
  <activeProfiles><activeProfile>hauntedmc</activeProfile></activeProfiles>
</settings>
```

Each HauntedMC repository commits an equivalent `.mvn/settings.xml` and `.mvn/maven.config` so parent resolution happens before Maven reads the project POM, and so packaged Maven-plugin dependencies such as the shared Checkstyle rules resolve from GitHub Packages. CI supplies `PACKAGES_USER` and `PACKAGES_TOKEN` from GitHub Actions secrets.

## Parent selection and version ownership

Reusable libraries inherit the library parent and must not import the ecosystem BOM:

```xml
<parent>
  <groupId>nl.hauntedmc.platform</groupId>
  <artifactId>haunted-library-parent</artifactId>
  <version>1.6.1</version>
  <relativePath/>
</parent>
```

Deployable HauntedMC applications inherit the application parent. It imports the ecosystem BOM and the direct Maven-precedence constraints required for the FeatureFramework compatibility graph:

```xml
<parent>
  <groupId>nl.hauntedmc.platform</groupId>
  <artifactId>haunted-application-parent</artifactId>
  <version>1.6.1</version>
  <relativePath/>
</parent>
```

Use `haunted-dependencies-bom` directly only for a build that intentionally does not inherit a HauntedPlatform parent. Libraries keep their own public compatibility versions where necessary; applications may retain local aliases such as `${featureframework.version}` only when they forward a `${haunted.*}` Platform property. Applications inheriting `haunted-application-parent` must not re-import the FeatureFramework or HauntedObservability BOMs, independently pin HauntedObservability modules, or override the Platform-selected DataProvider/DataRegistry foundation versions without an explicit compatibility reason. Do not re-import Adventure, OpenTelemetry, or other common third-party BOMs either.

HauntedPlatform selects the HauntedObservability release through `${haunted.observability.version}` and imports `haunted-observability-bom`; that BOM owns alignment of HauntedObservability's own modules only. Platform remains the compatibility authority for FeatureFramework, DataProvider, DataRegistry, HauntedObservability, and shared third-party versions as one tested application dependency set.

OpenTelemetry core artifacts are aligned through `io.opentelemetry:opentelemetry-bom` at `${haunted.opentelemetry.version}`. The unified JVM runtime telemetry library is managed separately through `${haunted.opentelemetry.runtime-telemetry.version}` because that artifact is currently published from the instrumentation alpha line. Keep that alpha implementation behind runtime/integration boundaries; do not expose its types from stable HauntedMC public APIs.

## Publishing and verification

The release workflow publishes the complete reactor to `HauntedMC/HauntedPlatform` using `HAUNTEDMC_PACKAGES_USERNAME` and `HAUNTEDMC_PACKAGES_TOKEN`. No Maven Central, signing, or Central Portal credentials are used.

`verification` contains external consumer fixtures for the third-party BOM, library parent, and application parent. The fixtures verify the OpenTelemetry SDK/exporter/runtime-telemetry dependency foundation as well as FeatureFramework, DataProvider, DataRegistry, HauntedObservability, Theme, Adventure, Gson, SLF4J, and the Paper/Velocity compatibility paths. HauntedObservability consumer fixtures deliberately omit module versions so the build proves that `haunted-application-parent` supplies the complete aligned observability graph. The fixtures use `<relativePath/>`; the release workflow runs them after publication with a fresh Maven repository, preventing reactor or local-cache resolution from masking publication defects.

The application parent contains direct Adventure and common-library constraints in addition to importing `haunted-platform-bom`. This is deliberate Maven precedence handling: an imported BOM cannot override conflicting management inherited through FeatureFramework. Consumers must not repeat those pins.

## Release policy

HauntedPlatform releases are immutable Git tags and GitHub Packages versions. Consumers use released parent artifact versions and immutable reusable-workflow tags such as `@v1.6.1`, never `@main`. A platform BOM release names only already published public foundation artifacts; public-library releases are aligned by a later Platform release.

For the maintained release procedure and the guarded version-update command, see [docs/releasing.md](docs/releasing.md). See [CHANGELOG.md](CHANGELOG.md) for upgrade notes.
