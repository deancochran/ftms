# Releasing FTMS packages

Packages are independently versioned; a version in one package does not imply a release of another. Prepare locally, review and merge the change, create the explicit tag on the reviewed `main` commit, verify artifacts, publish, then verify public artifacts and an installed consumer.

| Package / runbook | Tag | Workflow | Publication |
| --- | --- | --- | --- |
| [TypeScript](../packages/typescript/README.md) | `vVERSION` | `publish.yml` | npm (`next` for prereleases) |
| [Python](../packages/python/RELEASING.md) | `python-vVERSION` | `release-python.yml` | PyPI trusted publishing |
| [Kotlin](../packages/kotlin/docs/releasing.md) | `kotlin-vVERSION` | `release-kotlin.yml` | Maven Central |
| [Rust](../packages/rust/docs/releasing.md) | `rust-vVERSION` | `release-rust.yml` | crates.io |
| [Swift](../packages/swift/RELEASING.md) | `swift-vVERSION` | `release-swift.yml` | GitHub source/evidence release; SwiftPM revision pins |
| [C](../packages/c/docs/release-readiness.md) | `c-vVERSION` | `release-c.yml` | GitHub source release; Conan/vcpkg submissions are separate |
| [Dart](../packages/dart/RELEASING.md) | `dart-vVERSION` | `release-dart.yml` | pub.dev; first manual bootstrap, then protected tag/OIDC publishing |
| [C#](../packages/csharp/docs/releasing.md) | `csharp-vVERSION` | `release-csharp.yml` | NuGet Trusted Publishing through the protected `nuget` environment |
| [Go](../packages/go/docs/releasing.md) | `packages/go/vVERSION` | No automatic publication workflow; `go-ci.yml` verifies source | Nested Go module tag, public proxy/checksum database and isolated consumer verification |

Run `pnpm release:prepare PORT --dry-run` first. It is deliberately read-only:
version/changelog updates can require package-specific lockfile or metadata changes,
so make them in a reviewed PR using the package runbook. It never tags, pushes,
publishes, or contacts credentials; Python readiness retains PEP 440 validation.

### Release entry naming

Future GitHub release titles use **`FTMS LANGUAGE VERSION`**, with the native version
and no extra `v` prefix. Generate the title from the current package metadata with
`node tools/release-title.mjs PORT` (read-only). For example: `FTMS Go 0.1.0`,
`FTMS C# 0.1.0-alpha.1`, or `FTMS Python 0.1.0a2`. Put the registry/package ID,
exact tag/commit, public-consumer result and artifact checksums in the body.
Only create a publication evidence entry after public verification succeeds.

Existing automated C, Swift, Kotlin and Rust release titles already follow this
format. Other publication workflows do not automatically create GitHub entries;
record those as a separate authorized release-completion step using the generated
title and verified evidence. A missing GitHub entry does not imply an unpublished
registry package. Do not backfill historical releases without their exact evidence.

Do not rename historical releases or regenerate their notes from current source:
immutable tagged retry tooling can compare titles and bodies exactly. Preserve
historical tags, assets and metadata. Source documentation updates never authorize
republishing the same version with changed README, changelog or classifier bytes.
See [naming and versioning conventions](versioning.md#naming-conventions).

C# readiness validates canonical NuGet version identity, not public availability.
Its native verification remains credential-free. The tag-only release workflow
requires a signed annotated tag, main ancestry, all-host native checks and the
protected NuGet environment before publishing the exact tested artifacts.
See the [C# release runbook](../packages/csharp/docs/releasing.md).
Public verification must compare the tested archive's payload with the downloaded
package and verify NuGet's repository signature: repository signing changes the
archive hash without changing its payload. Never accept an existing version solely
because a push reports a duplicate.

For a coordinated release, run `pnpm release:prepare all --dry-run`. It checks all
nine packages' version metadata and changelogs, emits each intended version/tag, preserves every
failure in a JSON report, and exits nonzero if any package fails. CI retains this
as `release-metadata-readiness`. To save machine-readable JSON locally, use
`node tools/release-prepare.mjs all --dry-run > release-readiness.json` outside the
tracked source tree (or redirect to your approved temporary evidence directory).
This is **metadata-only preflight**, not a simulation of publication or a check
that a version is still available. Existing versions may already be immutable.
Go has no manifest package-version field: preflight reads its first versioned
changelog heading and emits the required nested-module tag, not `go-vVERSION`.

Retries are permitted only for the exact tag commit and verified artifact identity.
The C/Swift GitHub helper creates an absent release, continues matching assets,
uploads missing assets, rejects unexpected/different assets or a different tag
commit, and downloads the resulting assets to verify their hashes. PyPI and npm
verify public artifact integrity before accepting an existing version. npm also
downloads the exact public archive and runs an isolated installed consumer after
publication or a matching retry, retaining `npm-release-evidence`. Dart checks an
existing version's exact extracted file manifest and hosted consumer rather than
attempting another upload. No retry may replace published bytes.

## Coordinated release checklist

A full release is a tracked set of independent package releases, **not an atomic
cross-registry transaction**. Do not force every ecosystem to use one version or
push all tags indiscriminately. Do not retag an already published version to the
cleanup commit. Use [the release matrix](released-packages.md) as historical
evidence, then recheck live state before any authorized release.

1. Inventory all nine packages. For each, record the package version, intended
   tag, exact reviewed commit, target registry, and whether this is a new release
   or verification of an existing one. Select new versions from actual package
   changes; update each changelog, lockfile and package-specific metadata in the PR.
2. Run all-package metadata preflight and `pnpm site:verify`. Require the full CI
   matrix on the final reviewed commit (manual `CI` dispatch selects every port).
   Inspect compiler, corpus and isolated installation evidence from each package;
   `pnpm verify` covers TypeScript, not native ports. Missing/skipped required
   evidence is a blocker, not a pass.
3. Confirm registry ownership, protected tags, required checks, trusted publishers
   and environment reviewers with an administrator. Dart's first manual pub.dev
   upload and publisher setup are recorded in the release matrix; verify that the
   protected publisher remains configured before subsequent releases.
   Source scaffolds or future ports are not release targets.
4. After explicit integration and publication authorization, tag the exact
   reviewed `main` commit using each package's namespace. Push individual approved
   tags only. Follow the package runbook and inspect the tag workflow's identity
   gate before approving publication. A local tag is not proof of a pushed tag,
   registry upload or successful consumer.
5. Track every package independently through **prepared → verified → published →
   public-verified**. Record tag/commit, workflow run/attempt URL, archive hashes,
   corpus/contract hashes, installation reports and any failures. Do not call the
   coordinated release complete until every intended package is public-verified
   (or an explicit scope change is approved).
6. Update `docs/released-packages.md`, versioning/support summaries, package guides
   and site landing copy only from verified publication evidence. Build the site
   again; approved Pages deployment is separate from registry publication.

## Failure triage and recovery

| Failure stage | What to inspect | Safe next action |
| --- | --- | --- |
| Metadata or tag identity | Version/changelog, tag's resolved commit, clean state, main ancestry | Fix untagged source in a reviewed PR. Never move a public tag. |
| Compiler, conformance, docs or installation | Failing job and retained reports; exact source/corpus hashes; skipped cases | Fix the candidate and rerun required verification before publication. |
| Authentication or approval | Environment, tag restrictions, OIDC binding, registry ownership | Have an authorized administrator repair settings; do not substitute a long-lived token or bypass approval. |
| Upload timeout or partial upload | Exact registry version and public artifact hashes, not just the job conclusion | Treat publication state as unknown until checked. Resume only under the package's matching-artifact retry rules. |
| Public integrity or consumer failure after upload | Downloaded bytes, expected manifest, public verification report | Mark **published, verification failed**. Do not claim rollback or overwrite. Investigate; changed bytes require a new version. |
| Docs deployment only | `Documentation site` build/deploy and Pages settings | Correct/redeploy docs with approval; do not republish unchanged packages. |

Keep a failure record with package/version/tag/commit, failed stage, run URL,
expected/actual public identity and recovery decision. Retain artifact reports
before CI retention expires; redact credentials and private logs. Re-running a
publishing workflow can mutate remote state even when an existing version is
expected, and requires explicit authorization. Partial success in one registry
does not authorize continuing the other releases blindly.

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
the Dart `pub-dev` environment/trusted publisher after its first manual publication.
Confirm environment restrictions separately. No settings changes are performed by these
scripts. Pages retains `PAGES_ENABLED=true` and the `github-pages` environment;
merging to `main` automatically builds and deploys the site when Pages is enabled.
Manual `Documentation site` dispatch on main can rebuild/redeploy it independently.

The readiness command validates metadata only, not compiler/conformance evidence,
registry configuration, branch ancestry or authorization to publish. Follow each
package's runbook for those checks. Re-running a tag workflow is a remote action
and must be explicitly authorized even when the intended result is verification.
