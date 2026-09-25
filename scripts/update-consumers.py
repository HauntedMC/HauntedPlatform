#!/usr/bin/env python3
"""Reconcile reviewed internal-dependency PRs after a verified package release.

Runs in the HauntedPlatform repository with a GitHub App installation token.
It never merges or publishes a consumer. ProxyFeatures and ServerFeatures
temporarily verify locally while their GitHub Actions are disabled.
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
LOCAL_VERIFICATION_TARGETS = {"proxyfeatures", "serverfeatures"}
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
    "dungeons": ("Dungeons", "pom.xml", "v"),
    "ailex": ("AIlex", "pom.xml", "v"),
    "craftgpt": ("CraftGPT", "pom.xml", "v"),
    "velocityhotreloader": ("VelocityHotReloader", "pom.xml", "v"),
    "paperhotreloader": ("PaperHotReloader", "pom.xml", "v"),
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
    ("dungeons", (), {}, None),
    ("ailex", (), {}, None),
    ("craftgpt", (), {}, None),
    ("velocityhotreloader", (), {}, None),
    ("paperhotreloader", (), {}, None),
]


def run(*args, cwd=None, input=None):
    result = subprocess.run(args, cwd=cwd, input=input, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def gh_json(path):
    return json.loads(run("gh", "api", path))


def gh_json_pages(path):
    items = []
    page = 1
    while True:
        separator = "&" if "?" in path else "?"
        batch = gh_json(f"{path}{separator}per_page=100&page={page}")
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


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
            by_repo[repo] = gh_json_pages(f"repos/{ORG}/{repo}/releases")
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


def open_pulls(key):
    repo, _, _ = PROJECTS[key]
    return gh_json_pages(f"repos/{ORG}/{repo}/pulls?state=open")


def manual_version_pr(key, pulls):
    prefix = f"release/{key}-" if key in ("palette", "adapter") else "release/v"
    return any(pr["head"]["ref"].startswith(prefix) for pr in pulls)


def main_pom(key):
    repo, path, _ = PROJECTS[key]
    content = gh_json(f"repos/{ORG}/{repo}/contents/{path}?ref=main")
    return base64.b64decode(content["content"]).decode()


def pending(key, versions):
    repo, _, _ = PROJECTS[key]
    name = branch_for(key)
    pulls = open_pulls(key)
    if any(pr["head"]["ref"] == name for pr in pulls) or manual_version_pr(key, pulls):
        return True
    pom = main_pom(key)
    latest = versions.get(key)
    if key not in LOCAL_VERIFICATION_TARGETS and latest and semver(current_revision(pom)) > semver(latest):
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


def dependency_versions_match(content, properties, versions):
    platform = versions.get("platform")
    if platform:
        match = re.search(
            r"<parent>\s*<groupId>nl\.hauntedmc\.platform</groupId>\s*"
            r"<artifactId>haunted-(?:library|application)-parent</artifactId>\s*"
            r"<version>([^<]+)</version>", content
        )
        if not match or match.group(1) != platform:
            return False
    for property_name, producer in properties.items():
        desired = versions.get(producer)
        if not desired:
            continue
        match = re.search(rf"<{re.escape(property_name)}>([^<]+)</{re.escape(property_name)}>",
                          content)
        if not match or match.group(1) != desired:
            return False
    return True


def validate_graph():
    """Fail visibly when the configured graph no longer matches consumer POMs."""
    seen = {"platform"}
    for key, upstream, properties, _ in TARGETS:
        if key not in PROJECTS or any(dependency not in seen for dependency in upstream):
            raise ValueError(f"Invalid release-graph order at {key}")
        seen.add(key)
        pom = main_pom(key)
        current_revision(pom)
        if not re.search(
            r"<parent>\s*<groupId>nl\.hauntedmc\.platform</groupId>\s*"
            r"<artifactId>haunted-(?:library|application)-parent</artifactId>", pom
        ):
            raise ValueError(f"{key}: missing HauntedPlatform parent")
        for property_name in properties:
            expression = rf"<{re.escape(property_name)}>[^<]+</{re.escape(property_name)}>"
            if len(re.findall(expression, pom)) != 1:
                raise ValueError(f"{key}: expected one {property_name} in its POM")


def reconcile(key, properties, module, versions):
    repo, pom_path, _ = PROJECTS[key]
    if manual_version_pr(key, open_pulls(key)):
        print(f"{repo}/{key}: waiting for a human version PR", flush=True)
        return
    base_pom = main_pom(key)
    own_release = versions.get(key)
    if key not in LOCAL_VERIFICATION_TARGETS and own_release and semver(current_revision(base_pom)) > semver(own_release):
        print(f"{repo}/{key}: waiting for its merged release to publish", flush=True)
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
    if not changes:
        print(f"{repo}/{key}: already aligned", flush=True)
        return
    with tempfile.TemporaryDirectory(prefix=f"haunted-update-{key}-") as directory:
        work = Path(directory) / repo
        run("git", "clone", "--quiet", f"https://github.com/{ORG}/{repo}.git", str(work))
        run("git", "config", "user.name", "hauntedmc-release-bot", cwd=work)
        run("git", "config", "user.email", "release-bot@users.noreply.github.com", cwd=work)
        branch = branch_for(key)
        existing = next((pr for pr in open_pulls(key)
                         if pr["head"]["ref"] == branch), None)
        if existing:
            run("git", "fetch", "--quiet", "origin", branch, cwd=work)
            main_sha = run("git", "rev-parse", "HEAD", cwd=work).strip()
            ancestor = run("git", "merge-base", "HEAD", "FETCH_HEAD", cwd=work).strip()
            remote_pom = run("git", "show", f"FETCH_HEAD:{pom_path}", cwd=work)
            major, minor, patch = semver(current_revision(base_pom))
            next_version = f"{major}.{minor}.{patch + 1}"
            aligned = (dependency_versions_match(remote_pom, properties, versions)
                       and current_revision(remote_pom) == next_version)
            if ancestor == main_sha and aligned:
                print(f"{repo}/{key}: existing PR is current", flush=True)
                return
        prepare = "./tools/release/prepare-version.sh"
        if module:
            run(prepare, module, "patch", cwd=work)
        else:
            run(prepare, "patch", cwd=work)
        pom = work / pom_path
        original = pom.read_text()
        updated = original
        if platform:
            updated, _ = replace_parent(updated, platform)
        for property_name, producer in properties.items():
            latest = versions.get(producer)
            if latest:
                updated, _ = replace_property(updated, property_name, latest)
        pom.write_text(updated)
        run("git", "diff", "--check", cwd=work)
        run("git", "add", "-A", cwd=work)
        run("git", "commit", "-m", "chore: align published HauntedMC dependencies", cwd=work)
        verification = (
            "GitHub Actions are paused for this repository. This PR is a draft until "
            "`gh haunted-release verify-pr NUMBER` passes locally at the current head. "
            "Merging will not publish or notify downstream repositories while Actions are disabled.\n"
            if key in LOCAL_VERIFICATION_TARGETS else
            "Merge after this repository's CI passes; its release workflow will publish "
            "and verify the package before notifying downstream projects.\n"
        )
        body = (
            "Align this project with already published HauntedMC releases. "
            "The release workflow verified each package from a fresh Maven repository before tagging.\n\n"
            + "\n".join(f"- {change}" for change in changes)
            + "\n\nThis PR also prepares a patch version. " + verification
        )
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as body_file:
            body_file.write(body)
            body_file.flush()
            run(
                "gh", "haunted-release", "publish-pr", "--branch", branch,
                "--title", "chore: align published HauntedMC dependencies",
                "--body-file", body_file.name, cwd=work,
            )
        print(f"{repo}/{key}: opened or refreshed PR for {', '.join(changes)}", flush=True)


def main():
    payload = json.loads(os.environ.get("RELEASE_PAYLOAD", "{}"))
    allowed = {name for name, _, _ in PROJECTS.values()} | {
        "hauntedmc-theme-palette", "hauntedmc-theme-featureframework"
    }
    scheduled = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    if not scheduled and (payload.get("producer") not in allowed or not re.fullmatch(
        r"\d+\.\d+\.\d+", str(payload.get("version", ""))
    )):
        raise SystemExit("Invalid or missing release notification")
    producer = None if scheduled else {
        "HauntedPlatform": "platform",
        "HauntedObservability": "observability",
        "hauntedmc-theme-palette": "palette",
        "hauntedmc-theme-featureframework": "adapter",
    }.get(payload["producer"], payload["producer"].lower())
    for attempt in range(6):
        versions = published_versions()
        if scheduled or (versions.get(producer) and semver(versions[producer]) >= semver(payload["version"])):
            break
        if attempt == 5:
            raise SystemExit(f"Release {payload['producer']} {payload['version']} is not visible yet")
        time.sleep(5)
    run("gh", "auth", "setup-git")
    validate_graph()
    for key, upstream, properties, module in TARGETS:
        if any(pending(dep, versions) for dep in upstream):
            print(f"{PROJECTS[key][0]}/{key}: waiting for upstream reviewed PR or publication", flush=True)
            continue
        reconcile(key, properties, module, versions)


if __name__ == "__main__":
    main()
