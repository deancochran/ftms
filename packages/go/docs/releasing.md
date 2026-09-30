# Go release gates — no release has been performed

The package is an unreleased source candidate. Complete the parity target and
interface review before the proposed first `v0.1.0`; do not tag a placeholder or
describe this local milestone as published.

## Identity

- Module: `github.com/deancochran/ftms/packages/go`
- Package: `ftms`
- Example consumer version: `v0.1.0`
- Required repository tag: **`packages/go/v0.1.0`**

Go requires the subdirectory prefix on nested-module version tags. `go-v0.1.0`
would not publish this version correctly. The `go` directive in `go.mod` is a
toolchain minimum, not the package version. No duplicate `VERSION` authority is
needed; the immutable tag and matching changelog identify a release. Package,
specification, corpus schema and corpus content versions remain independent.

## Before explicit release authorization

1. Complete and review the intended support profile, exported interface docs,
   pending corpus accounting, safety exclusions, and changelog.
2. Run `bash scripts/verify.sh` on a clean proposed release commit under the
   minimum supported Go toolchain and current supported toolchains.
3. Run bounded fuzzing, inspect coverage gaps, review the module zip and license,
   and preserve all verification reports with corpus identities.
4. Confirm public repository ownership and the exact module path. Do not change
   existing npm exports, other package tags, or shared fixtures to release Go.
5. Obtain authorization to commit/push/tag/publish. Implementation permission is
   not release permission. No release workflow is enabled in this milestone.

## Authorized publication and public verification

After the approved clean commit and immutable `packages/go/vVERSION` tag are
published to GitHub, request the exact module through the public proxy:

```sh
GOPROXY=https://proxy.golang.org \
  go list -m github.com/deancochran/ftms/packages/go@v0.1.0
```

This is a publication/indexing action, not a pre-release local smoke test. Use
only after authorization. Go consumes tagged repository source: there is no
npm-style registry upload or Go registry account/token.

In a fresh external module and fresh module cache, with `GOWORK=off`, no `replace`,
and the normal public checksum database enabled:

1. Fetch the exact version using `go get`.
2. Record `go mod download -json` identity and checksums.
3. Compile and run a consumer covering measurements, controls, capabilities and,
   once implemented, record operations.
4. Confirm the module zip contains the intended files, license, and no private
   context or independent fixture copies.
5. Confirm pkg.go.dev displays documentation for that exact version separately.

Only after those checks update the canonical `docs/released-packages.md` and
project overview with the exact version/tag, commit, installation instructions,
toolchains, checksums, corpus identities, and limits. An optional GitHub release
can attach evidence but is not the Go module distribution mechanism.

Never move, reuse, or overwrite a published version tag. Fix a bad release with
a new version (and a deliberate Go retraction if needed), not rewritten history.
A future v2 requires the `/v2` module/import path convention.

References:
- https://go.dev/doc/modules/managing-source
- https://go.dev/doc/modules/publishing
