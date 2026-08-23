# HauntedPlatform

HauntedPlatform is the Java build and dependency-management standard for HauntedMC software. It contains no Minecraft runtime or gameplay code.

| Artifact | Intended use |
| --- | --- |
| `haunted-parent` | Java 25, plugin policy, Enforcer, Checkstyle, generic JaCoCo, flattening, and deployment policy. |
| `haunted-library-parent` | Parent for reusable libraries; imports only `haunted-dependencies-bom`. |
| `haunted-application-parent` | Parent for deployable HauntedMC applications; imports `haunted-platform-bom`. |
| `haunted-dependencies-bom` | Shared platform-neutral third-party versions. |
| `haunted-platform-bom` | Validated public HauntedMC foundation-library versions and FeatureFramework's own BOM. |
| `haunted-build-rules` | Packaged Checkstyle configuration consumed by the shared parent. |

FeatureFramework, DataProvider, and DataRegistry use `haunted-library-parent`. ServerFeatures and ProxyFeatures use `haunted-application-parent`. Runtime targets, shading, acceptance tests, project metadata, release locations, and coverage thresholds remain in their owning repositories.

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

## Publishing and verification

The release workflow publishes the complete reactor to `HauntedMC/HauntedPlatform` using `HAUNTEDMC_PACKAGES_USERNAME` and `HAUNTEDMC_PACKAGES_TOKEN`. No Maven Central, signing, or Central Portal credentials are used.

`verification` contains external consumer fixtures for the third-party BOM, library parent, and application parent. They use `<relativePath/>` and are run after publication as well as during local validation.
