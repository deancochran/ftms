# Releasing FTMS packages

Packages are independently versioned; a version in one package does not imply a release of another. Prepare locally, review and merge the change, create the explicit tag on the reviewed `main` commit, verify artifacts, publish, then verify public artifacts and an installed consumer.

| Package | Tag | Publication |
| --- | --- | --- |
| TypeScript | `vVERSION` | npm (`next` for prereleases) |
| Python | `python-vVERSION` | PyPI trusted publishing |
| Kotlin | `kotlin-vVERSION` | Maven Central |
| Rust | `rust-vVERSION` | crates.io |
| Swift | `swift-vVERSION` | GitHub source/evidence release |
| C | `c-vVERSION` | GitHub source release |
| C# | `csharp-vVERSION` (reserved) | Local NuGet prerelease artifacts only; publication not configured and requires separate authorization |

Run `pnpm release:prepare PORT --dry-run` first. It is deliberately read-only:
version/changelog updates can require package-specific lockfile or metadata changes,
so make them in a reviewed PR using the package runbook. It never tags, pushes,
publishes, or contacts credentials; Python readiness retains PEP 440 validation.

C# readiness validates canonical NuGet version identity, not NuGet ownership or
publication readiness. Its credential-free native workflow verifies local
artifacts only. Before enabling a tag publisher, review account/package ownership,
signed-tag identity, the protected NuGet environment and trusted-publishing policy.
Public verification must compare the tested archive's payload with the downloaded
package and verify NuGet's repository signature: repository signing changes the
archive hash without changing its payload. Never accept an existing version solely
because a push reports a duplicate.

Retries are idempotent only for the exact tag commit and exact artifact hashes: an absent GitHub release is created, matching assets continue, missing assets upload, and a different asset or target commit fails. PyPI and npm releases likewise verify public artifact integrity before accepting an existing version; retries never replace published bytes.

Administrators separately roll out protected tags, required-check migration, OIDC environments/trusted publishers, and registry authorization. Workflow code cannot establish remote settings. The `main` documentation site is current-source documentation, not an automatically versioned latest release. Swift remains consumed by immutable Git revision, and C Conan/vcpkg submissions remain separate.

## CI and settings rollout

`CI` is the PR/main entry point. Its `CI summary` check requires all selected
port checks, workflow/helper tests and documentation checks to finish successfully.
Package changes select that port and docs; shared contracts, workflow/tooling and
unknown root changes conservatively select every port. Docs-only changes select
docs. Manual CI runs select everything. Language workflows remain manually runnable
and reusable by release gates; they no longer duplicate PR/main runs.

Before relying on selective checks, update branch protection/rulesets to require
`CI summary` instead of the former individual language or docs job checks. Confirm
the exact displayed check name on an approved PR. Do not leave old required checks
configured: intentionally skipped or renamed checks can block merging.

Keep npm's trusted publisher bound to `publish.yml`, PyPI's to
`release-python.yml` and environment `pypi`, and the existing package environments
and credentials for Maven Central/crates.io. Confirm protected release tags and
environment restrictions separately. No settings changes are performed by these
scripts. Pages retains `PAGES_ENABLED=true` and the `github-pages` environment;
manual `Documentation site` dispatch on main can rebuild/redeploy it independently.

The readiness command validates metadata only, not compiler/conformance evidence,
registry configuration, branch ancestry or authorization to publish. Follow each
package's runbook for those checks. Re-running a tag workflow is a remote action
and must be explicitly authorized even when the intended result is verification.
