# Updating and releasing HauntedPlatform

HauntedPlatform releases are compatibility decisions, not routine bulk dependency upgrades. Make a small, reviewed change for each policy, plugin, third-party dependency, or foundation-library alignment change.

## Prepare a release

1. Start from current `main` on a clean worktree and choose the next immutable `major.minor.patch` version.
2. Update Platform's own version references before making other tracked changes:

   ```bash
   scripts/prepare-release.sh 1.4.0
   ```

   The script updates the root version, SCM tag, internal parent/BOM references, external verification fixtures, and README examples. It refuses a dirty tracked worktree and fails if it leaves an old Platform version in those files.

   It intentionally does **not** change `CHANGELOG.md`, third-party dependency catalog entries, or the public foundation-library versions in `haunted-platform-bom`. Review and edit those deliberately.
3. Make the intended policy or dependency-management changes. Keep runtime/gameplay and project-specific compatibility concerns out of this repository, and add a concise `CHANGELOG.md` entry describing the impact and any consumer action.
4. Run the complete validation:

   ```bash
   mvn -U -B -ntp clean verify
   mvn -U -B -ntp clean install
   mvn -U -B -ntp dependency:tree help:effective-pom

   mvn -U -B -ntp -f verification/bom-consumer/pom.xml clean verify
   mvn -U -B -ntp -f verification/library-parent-consumer/pom.xml clean verify
   mvn -U -B -ntp -f verification/application-parent-consumer/pom.xml clean verify
   mvn -U -B -ntp -f verification/application-graph-regression/pom.xml clean verify
   ```

   For the strongest local check, use one empty `-Dmaven.repo.local=<temporary-directory>` for `clean install` and all four fixture commands, exactly as CI does.
5. Open and merge the Platform PR. Do not publish from a branch.
6. Create and push an annotated tag that exactly matches the root version:

   ```bash
   git tag -a v1.4.0 -m 'HauntedPlatform 1.4.0'
   git push origin v1.4.0
   ```

   The tag-only release workflow validates the version, installs and tests against an isolated repository, deploys the entire reactor atomically with `-DdeployAtEnd=true`, and then tests the deployed artifacts from a fresh repository. It is the only publication path.

## Updating the ecosystem BOM

Release FeatureFramework, DataProvider, DataRegistry, HauntedObservability, or Theme first. Only after a public version is published may a later HauntedPlatform release update the corresponding `haunted-platform-bom` property or imported foundation BOM. Never put an unreleased foundation-library version in the Platform BOM.

FeatureFramework and HauntedObservability own alignment of their own modules through their published BOMs. HauntedPlatform selects the exact released BOM versions and remains the compatibility authority for the complete application set. DataProvider and DataRegistry modules remain directly aligned in `haunted-platform-bom` until those projects deliberately publish their own BOMs.

Applications inheriting `haunted-application-parent` must consume the Platform-selected ecosystem rather than re-importing FeatureFramework or HauntedObservability BOMs or independently pinning their module versions. Reusable libraries continue to inherit `haunted-library-parent`, which imports only the platform-neutral third-party BOM.

After the Platform release has passed its post-deployment smoke test, update consumer repositories to the new parent/BOM version and run each repository's full CI and runtime/acceptance profiles. Keep applications' Paper/Velocity targets, external plugin APIs, shading, coverage gates, and other local compatibility controls in the application repository.
