# Contributing to HauntedPlatform

HauntedPlatform owns external dependency versions, Maven parent behavior, and
build rules shared by HauntedMC projects. Consumer repositories own their
internal HauntedMC dependency versions.

Start from `main` and keep a pull request focused on one policy or release
change. Explain affected consumers and any compatibility impact. Do not commit
package credentials. For a Platform version update, use
`./tools/release/update-version X.Y.Z --pr` from a clean, current `main`
worktree. The shared release CLI opens the PR; merging it starts publication
only after required CI passes.

Run `python3 -m unittest discover -s scripts -p 'test_*.py'` for release
automation changes and `mvn -U -B -ntp clean verify` for build policy changes.
Changes to parents or BOMs should also pass the consumer fixtures in
`verification/`; CI runs them on every PR.

Report security issues privately through [SECURITY.md](SECURITY.md).

## Fork pull requests

Fork PRs run with a read-only GitHub token and receive no repository package secrets. CI attempts to resolve public HauntedMC Maven packages with that token and still runs static checks. If GitHub Packages denies cross-repository access, the required Maven check cannot pass on the fork; a maintainer reviews the change and opens an upstream branch PR for full CI before merge. Never include a package token in a PR or build log.
