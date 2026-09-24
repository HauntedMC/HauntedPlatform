#!/usr/bin/env python3
"""Reconcile reviewed internal-dependency PRs after a verified package release.

Runs in the HauntedPlatform repository with a GitHub App installation token.
It never merges or publishes a consumer. Each consumer's own CI and release
workflow remain the authority for that repository.
"""
import base64
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

ORG = "HauntedMC"
BRANCH = "automation/internal-dependencies"
PROJECTS = {
    "platform": ("HauntedPlatform", "pom.xml", "v"),
    "palette": ("Theme", "hauntedmc-theme-palette/pom.xml", "palette-v"),
    "dataprovider": ("DataProvider", "pom.xml", "v"),
    "dataregistry": ("DataRegistry", "pom.xml", "v"),
    "featureframework": ("FeatureFramework", "pom.xml", "v"),
    "adapter": ("Theme", "hauntedmc-theme-featureframework/pom.xml", "adapter-v"),
    "observability": ("HauntedObservability", "pom.xml", "v"),
    "proxyfeatures": ("ProxyFeatures", "pom.xml", "v"),
    "serverfeatures": ("ServerFeatures", "pom.xml", "v"),
}
TARGETS = [
    ("palette", (), {}, "palette"),
    ("dataprovider", ("palette",), {"haunted.theme.version": "palette"}, None),
    ("dataregistry", ("palette", "dataprovider"), {
        "haunted.theme.version": "palette",
        "haunted.dataprovider.version": "dataprovider",
    }, None),
    ("featureframework", ("dataprovider", "dataregistry"), {
        "haunted.dataprovider.version": "dataprovider",
        "haunted.dataregistry.version": "dataregistry",
    }, None),
    ("adapter", ("palette", "featureframework"), {
        "haunted.theme.palette.version": "palette",
        "haunted.featureframework.version": "featureframework",
    }, "adapter"),
    ("observability", ("dataprovider", "dataregistry", "featureframework"), {
        "haunted.dataprovider.version": "dataprovider",
        "haunted.dataregistry.version": "dataregistry",
        "haunted.featureframework.version": "featureframework",
    }, None),
    ("proxyfeatures", ("dataprovider", "dataregistry", "featureframework", "palette", "adapter", "observability"), {
        "haunted.dataprovider.version": "dataprovider",
        "haunted.dataregistry.version": "dataregistry",
        "haunted.featureframework.version": "featureframework",
        "haunted.theme.palette.version": "palette",
        "haunted.theme.adapter.version": "adapter",
        "haunted.observability.version": "observability",
    }, None),
    ("serverfeatures", ("proxyfeatures", "dataprovider", "dataregistry", "featureframework", "palette", "adapter", "observability"), {
        "haunted.dataprovider.version": "dataprovider",
        "haunted.dataregistry.version": "dataregistry",
        "haunted.featureframework.version": "featureframework",
        "haunted.theme.palette.version": "palette",
        "haunted.theme.adapter.version": "adapter",
        "haunted.observability.version": "observability",
        "haunted.proxyfeatures.contracts.version": "proxyfeatures",
    }, None),
]


def run(*args, cwd=None, input=None):
    result = subprocess.run(args, cwd=cwd, input=input, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def gh_json(path):
    return json.loads(run("gh", "api", path))


def semver(value):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(f"Invalid semantic version: {value!r}")
    return tuple(map(int, match.groups()))


def current_revision(pom):
    match = re.search(r"<revision>(\d+\.\d+\.\d+)</revision>", pom)
    if not match:
        raise ValueError("Root/module POM has no semantic revision")
    return match.group(1)


def published_versions():
    result = {}
    by_repo = {}
    for repo, _, _ in PROJECTS.values():
        if repo not in by_repo:
            by_repo[repo] = gh_json(f"repos/{ORG}/{repo}/releases?per_page=100")
    for key, (repo, _, prefix) in PROJECTS.items():
        versions = [
            release["tag_name"][len(prefix):]
            for release in by_repo[repo]
            if not release["draft"] and not release["prerelease"]
            and release["tag_name"].startswith(prefix)
            and re.fullmatch(r"\d+\.\d+\.\d+", release["tag_name"][len(prefix):])
        ]
        result[key] = max(versions, key=semver) if versions else None
    return result


def branch_for(key):
    return f"automation/internal-{key}" if key in ("palette", "adapter") else BRANCH


def main_pom(key):
    repo, path, _ = PROJECTS[key]
    content = gh_json(f"repos/{ORG}/{repo}/contents/{path}?ref=main")
    return base64.b64decode(content["content"]).decode()


def pending(key, versions):
    repo, _, _ = PROJECTS[key]
    name = branch_for(key)
    pulls = gh_json(f"repos/{ORG}/{repo}/pulls?state=open&per_page=100")
    if any(pr["head"]["ref"] == name for pr in pulls):
        return True
    pom = main_pom(key)
    latest = versions.get(key)
    if latest and semver(current_revision(pom)) > semver(latest):
        return True
    platform = versions.get("platform")
    if platform:
        try:
            _, outdated = replace_parent(pom, platform)
        except ValueError:
            return True
        if outdated:
            return True
    properties = next(target[2] for target in TARGETS if target[0] == key)
    for property_name, producer in properties.items():
        desired = versions.get(producer)
        if desired:
            try:
                _, outdated = replace_property(pom, property_name, desired)
            except ValueError:
                return True
            if outdated:
                return True
    return False


def replace_property(content, name, desired):
    pattern = re.compile(rf"(<{re.escape(name)}>)([^<]+)(</{re.escape(name)}>)")
    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} property; found {len(matches)}")
    old = matches[0].group(2)
    if semver(desired) <= semver(old):
        return content, False
    return pattern.sub(lambda match: match.group(1) + desired + match.group(3), content), True


def replace_parent(content, desired):
    pattern = re.compile(
        r"(<parent>\s*<groupId>nl\.hauntedmc\.platform</groupId>\s*"
        r"<artifactId>haunted-(?:library|application)-parent</artifactId>\s*"
        r"<version>)([^<]+)(</version>)"
    )
    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        raise ValueError(f"Expected one HauntedPlatform parent; found {len(matches)}")
    old = matches[0].group(2)
    if semver(desired) <= semver(old):
        return content, False
    return pattern.sub(lambda match: match.group(1) + desired + match.group(3), content), True


def reconcile(key, properties, module, versions):
    repo, pom_path, _ = PROJECTS[key]
    base_pom = main_pom(key)
    own_release = versions.get(key)
    if own_release and semver(current_revision(base_pom)) > semver(own_release):
        print(f"{repo}/{key}: waiting for its merged release to publish", flush=True)
        return
    if "nl.hauntedmc.platform" not in base_pom:
        print(f"{repo}/{key}: waiting for parent migration PR", flush=True)
        return
    missing = [name for name in properties if f"<{name}>" not in base_pom]
    if missing:
        print(f"{repo}/{key}: waiting for internal-version migration PR ({', '.join(missing)})", flush=True)
        return
    desired = base_pom
    changes = []
    platform = versions.get("platform")
    if platform:
        desired, changed = replace_parent(desired, platform)
        if changed:
            changes.append(f"HauntedPlatform parent → {platform}")
    for property_name, producer in properties.items():
        latest = versions.get(producer)
        if latest:
            desired, changed = replace_property(desired, property_name, latest)
            if changed:
                changes.append(f"{property_name} → {latest}")
    remove_legacy_helper = (
        key == "dataprovider" and platform is not None
        and semver(platform) >= (2, 0, 0)
        and "<build.helper.maven.plugin.version>" in base_pom
    )
    if remove_legacy_helper:
        changes.append("build-helper plugin version → inherited from Platform")
    if not changes:
        print(f"{repo}/{key}: already aligned", flush=True)
        return
    with tempfile.TemporaryDirectory(prefix=f"haunted-update-{key}-") as directory:
        work = Path(directory) / repo
        run("git", "clone", "--quiet", f"https://github.com/{ORG}/{repo}.git", str(work))
        run("git", "config", "user.name", "hauntedmc-release-bot", cwd=work)
        run("git", "config", "user.email", "release-bot@users.noreply.github.com", cwd=work)
        if module:
            run("./update_version.sh", module, "patch", cwd=work)
        else:
            run("./update_version.sh", "patch", cwd=work)
        pom = work / pom_path
        original = pom.read_text()
        updated = original
        if platform:
            updated, _ = replace_parent(updated, platform)
        for property_name, producer in properties.items():
            latest = versions.get(producer)
            if latest:
                updated, _ = replace_property(updated, property_name, latest)
        if remove_legacy_helper:
            updated, removed = re.subn(
                r"^\s*<build\.helper\.maven\.plugin\.version>[^<]+"
                r"</build\.helper\.maven\.plugin\.version>\n",
                "", updated, count=1, flags=re.MULTILINE,
            )
            if removed != 1:
                raise ValueError("Expected one legacy build-helper override")
        pom.write_text(updated)
        run("git", "diff", "--check", cwd=work)
        run("git", "add", "-A", cwd=work)
        run("git", "commit", "-m", "chore: align published HauntedMC dependencies", cwd=work)
        branch = branch_for(key)
        remote = subprocess.run(
            ["git", "fetch", "--quiet", "origin", f"refs/heads/{branch}:refs/remotes/origin/{branch}"],
            cwd=work, capture_output=True, text=True,
        )
        if remote.returncode == 0:
            same = subprocess.run(
                ["git", "diff", "--quiet", "HEAD", f"origin/{branch}"],
                cwd=work,
            ).returncode == 0
            if same:
                print(f"{repo}/{key}: existing PR is current", flush=True)
                return
        run("git", "push", "--quiet", "--force-with-lease", "origin", f"HEAD:refs/heads/{branch}", cwd=work)
        pulls = gh_json(f"repos/{ORG}/{repo}/pulls?state=open&head={ORG}:{branch}&per_page=100")
        body = (
            "Align this project with already published HauntedMC releases. "
            "The release workflow verified each package from a fresh Maven repository before tagging.\n\n"
            + "\n".join(f"- {change}" for change in changes)
            + "\n\nThis PR also prepares a patch release. Merge after this repository's CI passes; "
            "its release workflow will publish and verify the package before notifying downstream projects.\n"
        )
        if pulls:
            run("gh", "pr", "edit", str(pulls[0]["number"]), "--repo", f"{ORG}/{repo}",
                "--body", body, cwd=work)
        else:
            run("gh", "pr", "create", "--repo", f"{ORG}/{repo}", "--base", "main",
                "--head", branch, "--title", "chore: align published HauntedMC dependencies",
                "--body", body, cwd=work)
        print(f"{repo}/{key}: opened or refreshed PR for {', '.join(changes)}", flush=True)


def main():
    payload = json.loads(os.environ.get("RELEASE_PAYLOAD", "{}"))
    allowed = {name for name, _, _ in PROJECTS.values()} | {
        "hauntedmc-theme-palette", "hauntedmc-theme-featureframework"
    }
    if payload.get("producer") not in allowed or not re.fullmatch(
        r"\d+\.\d+\.\d+", str(payload.get("version", ""))
    ):
        raise SystemExit("Invalid or missing release notification")
    producer = {
        "HauntedPlatform": "platform",
        "HauntedObservability": "observability",
        "hauntedmc-theme-palette": "palette",
        "hauntedmc-theme-featureframework": "adapter",
    }.get(payload["producer"], payload["producer"].lower())
    for attempt in range(6):
        versions = published_versions()
        if versions.get(producer) and semver(versions[producer]) >= semver(payload["version"]):
            break
        if attempt == 5:
            raise SystemExit(f"Release {payload['producer']} {payload['version']} is not visible yet")
        time.sleep(5)
    run("gh", "auth", "setup-git")
    for key, upstream, properties, module in TARGETS:
        if any(pending(dep, versions) for dep in upstream):
            print(f"{PROJECTS[key][0]}/{key}: waiting for upstream reviewed PR or publication", flush=True)
            continue
        reconcile(key, properties, module, versions)


if __name__ == "__main__":
    main()
