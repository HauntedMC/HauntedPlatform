# HauntedPlatform

HauntedPlatform is the Java build and dependency-management standard for HauntedMC software. It contains no Minecraft runtime or gameplay code.

| Artifact | Intended use |
| --- | --- |
| `haunted-parent` | Java 25, plugin policy, Enforcer, Checkstyle, generic JaCoCo, flattening, and deployment policy. |
| `haunted-library-parent` | Parent for reusable libraries; imports only `haunted-dependencies-bom`. |
| `haunted-application-parent` | Parent for deployable HauntedMC applications; imports `haunted-platform-bom`. |
| `haunted-dependencies-bom` | Shared platform-neutral third-party versions, including Hibernate where it is shared across projects. |
| `haunted-platform-bom` | Validated public HauntedMC foundation-library versions, including all regular DataProvider/DataRegistry/Theme modules and FeatureFramework's own BOM. |
| `haunted-build-rules` | Packaged Checkstyle configuration consumed by the shared parent. |

FeatureFramework, DataProvider, DataRegistry, and Theme use `haunted-library-parent`. ServerFeatures and ProxyFeatures use `haunted-application-parent`. Runtime targets, shading, acceptance tests, project metadata, release locations, and coverage thresholds remain in their owning repositories.

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
  <version>1.2.0</version>
  <relativePath/>
</parent>
```

Deployable HauntedMC applications inherit the application parent. It imports the ecosystem BOM and the direct Maven-precedence constraints required for the FeatureFramework compatibility graph:

```xml
<parent>
  <groupId>nl.hauntedmc.platform</groupId>
  <artifactId>haunted-application-parent</artifactId>
  <version>1.2.0</version>
  <relativePath/>
</parent>
```

Use `haunted-dependencies-bom` directly only for a build that intentionally does not inherit a HauntedPlatform parent. Libraries keep their own public compatibility versions where necessary; applications may retain local aliases such as `${featureframework.version}` only when they forward a `${haunted.*}` Platform property. Do not re-import FeatureFramework, Adventure, or common third-party BOMs in an application that already inherits `haunted-application-parent`.

## Publishing and verification

The release workflow publishes the complete reactor to `HauntedMC/HauntedPlatform` using `HAUNTEDMC_PACKAGES_USERNAME` and `HAUNTEDMC_PACKAGES_TOKEN`. No Maven Central, signing, or Central Portal credentials are used.

`verification` contains external consumer fixtures for the third-party BOM, library parent, and application parent. The realistic application fixtures combine FeatureFramework, DataProvider, DataRegistry, Theme, Adventure, Gson, SLF4J, and the Paper/Velocity compatibility paths. They use `<relativePath/>`; the release workflow runs them after publication with a fresh Maven repository, preventing reactor or local-cache resolution from masking publication defects.

The application parent contains direct Adventure and common-library constraints in addition to importing `haunted-platform-bom`. This is deliberate Maven precedence handling: an imported BOM cannot override conflicting management inherited through FeatureFramework. Consumers must not repeat those pins.

## Release policy

HauntedPlatform releases are immutable Git tags and GitHub Packages versions. Consumers use released parent artifact versions and immutable reusable-workflow tags such as `@v1.2.0`, never `@main`. A platform BOM release names only already published public foundation artifacts; public-library releases are aligned by a later Platform release.

See [CHANGELOG.md](CHANGELOG.md) for upgrade notes.
