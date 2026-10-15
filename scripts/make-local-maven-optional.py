#!/usr/bin/env python3
"""Remove optional hauntedmc/local-maven from classic branch protection.

Requires an authenticated gh CLI with repository administration permission.
Runs read-only unless --apply is specified. Organization and repository
rulesets are reported, never modified: a shared ruleset may affect other repos.
"""
import argparse
import json
import subprocess
import sys

ORG = "HauntedMC"
BRANCH = "main"
CONTEXT = "hauntedmc/local-maven"
REPOS = ("ProxyFeatures", "ServerFeatures", "WebApp")


class APIError(Exception):
    def __init__(self, path, detail):
        super().__init__(f"{path}: {detail.strip()}")
        self.detail = detail.strip()


def gh(path, *, method="GET", payload=None):
    cmd = ["gh", "api", "--method", method, path]
    if payload is not None:
        cmd += ["--input", "-"]
    completed = subprocess.run(
        cmd, input=json.dumps(payload) if payload is not None else None,
        text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        raise APIError(path, completed.stderr)
    return json.loads(completed.stdout) if completed.stdout.strip() else None


def required_statuses(repo):
    path = f"repos/{ORG}/{repo}/branches/{BRANCH}/protection/required_status_checks"
    try:
        return gh(path)
    except APIError as error:
        if "404" in error.detail:
            return None
        raise


def without_local_check(data):
    contexts = [name for name in data.get("contexts", []) if name != CONTEXT]
    checks = [check for check in data.get("checks", []) if check.get("context") != CONTEXT]
    changed = len(contexts) != len(data.get("contexts", [])) or len(checks) != len(data.get("checks", []))
    return changed, {"strict": data["strict"], "contexts": contexts, "checks": checks}


def inspect_rulesets(repo):
    try:
        rules = gh(f"repos/{ORG}/{repo}/rulesets?includes_parents=true")
    except APIError as error:
        print(f"  Could not inspect rulesets: {error.detail}")
        return
    for rule in rules:
        if rule.get("enforcement") == "active":
            print(f"  Active ruleset (not modified): {rule.get('name')} "
                  f"[{rule.get('source')}, id={rule.get('id')}]")
    if rules:
        print(f"  Check applicable rulesets: https://github.com/{ORG}/{repo}/settings/rules")


def run(repos, apply):
    errors = 0
    for repo in repos:
        print(f"\n{ORG}/{repo} ({BRANCH})", flush=True)
        try:
            data = required_statuses(repo)
            if data is None:
                print("  No classic required-status-checks protection found.")
            else:
                changed, payload = without_local_check(data)
                if not changed:
                    print(f"  Classic protection already does not require {CONTEXT}.")
                elif apply:
                    path = f"repos/{ORG}/{repo}/branches/{BRANCH}/protection/required_status_checks"
                    gh(path, method="PATCH", payload=payload)
                    verified = required_statuses(repo)
                    if verified is None or without_local_check(verified)[0]:
                        raise RuntimeError("GitHub did not confirm status removal")
                    print(f"  Removed {CONTEXT}; other required checks and strict mode preserved.")
                else:
                    print(f"  Would remove {CONTEXT} from classic required checks.")
                    print(f"  Preserving {len(payload['contexts'])} contexts, "
                          f"{len(payload['checks'])} checks and strict={payload['strict']}.")
            inspect_rulesets(repo)
        except (APIError, ValueError, KeyError, RuntimeError) as error:
            errors += 1
            print(f"  ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Modify classic branch protection (default: read-only preview)")
    parser.add_argument("--repo", action="append", choices=REPOS, help="Limit to named repository")
    args = parser.parse_args()
    raise SystemExit(run(args.repo or REPOS, args.apply))
