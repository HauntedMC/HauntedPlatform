#!/usr/bin/env bash
# Updates HauntedPlatform's own release identity and every internal reference to it.
set -euo pipefail

usage() {
    printf 'Usage: %s <major.minor.patch>\n' "${0##*/}" >&2
    exit 64
}

[[ $# -eq 1 ]] || usage
next_version="$1"
[[ "$next_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    printf 'Release versions must use major.minor.patch (received %q).\n' "$next_version" >&2
    exit 64
}

repository_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    printf 'Run this script from a HauntedPlatform Git worktree.\n' >&2
    exit 1
}
cd "$repository_root"

[[ -f pom.xml && -f haunted-parent/pom.xml ]] || {
    printf 'This is not the HauntedPlatform repository root.\n' >&2
    exit 1
}

if ! git diff --quiet || ! git diff --cached --quiet; then
    printf 'Commit or stash tracked changes before preparing a release.\n' >&2
    exit 1
fi

current_version="$(perl -0777 -ne 'print $1 if m{<artifactId>haunted-platform</artifactId>\s*<version>([^<]+)</version>}s' pom.xml)"
[[ -n "$current_version" ]] || {
    printf 'Could not determine the current HauntedPlatform version from pom.xml.\n' >&2
    exit 1
}
[[ "$current_version" != "$next_version" ]] || {
    printf 'HauntedPlatform is already at %s.\n' "$next_version" >&2
    exit 1
}

files=(
    pom.xml
    README.md
    haunted-build-rules/pom.xml
    haunted-dependencies-bom/pom.xml
    haunted-parent/pom.xml
    haunted-library-parent/pom.xml
    haunted-platform-bom/pom.xml
    haunted-application-parent/pom.xml
    verification/pom.xml
    verification/bom-consumer/pom.xml
    verification/library-parent-consumer/pom.xml
    verification/application-parent-consumer/pom.xml
    verification/application-graph-regression/pom.xml
)

for file in "${files[@]}"; do
    perl -pi -e "s/\Q$current_version\E/$next_version/g" "$file"
done

if rg --fixed-strings --glob 'pom.xml' --glob 'README.md' "$current_version" \
    pom.xml haunted-* verification README.md; then
    printf 'A tracked Platform version reference still uses %s; resolve it before committing.\n' "$current_version" >&2
    exit 1
fi

git diff --check
printf 'Prepared HauntedPlatform %s -> %s.\n' "$current_version" "$next_version"
printf 'Next: review the diff, update CHANGELOG.md and any deliberately changed dependency/BOM versions, then run the release validation.\n'
