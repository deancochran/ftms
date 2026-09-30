# Rust verification and automated publishing

## Release contract

`Cargo.toml` is the package name/version authority. Rust uses **`rust-vVERSION`**
tags, independent of npm `v*`, C `c-v*`, Swift tags and other package versions.
For example, version `0.1.0` requires exactly `rust-v0.1.0`. SemVer prereleases
are supported; build-metadata suffixes are deliberately not release identities.
Every version needs an exact `## VERSION` heading in this package's changelog.

The initial release scope includes the raw codecs, static capability evidence,
normalized views, and bounded record planning/assembly documented in the README.
It does not include BLE lifecycle management or device qualification. See
`verification.md` for corpus-specific coverage and unsupported cases.

## Pipeline

`.github/workflows/native-rust.yml` runs on manual verification dispatches and
calls from the release workflow. It has no
publishing credentials. Its jobs cover:

- Linux on the pinned MSRV and current stable, plus macOS and Windows on stable;
- offline tests of release policy, formatting, Clippy, all Rust integration and
  Rustdoc tests, and strict documentation generation;
- Cortex-M0 compilation on Linux (not board execution);
- actual Cargo packaging and an isolated executable consumer of each exact
  archive, not just a source-path dependency in this checkout.

Each passing job uploads its `.crate`, `release.json`, `SHA256SUMS` and test log.
The record identifies source commit/dirty state, compiler/Cargo versions, archive
digest and shared input hashes. Input hashes do **not** claim unimplemented
corpora passed. The current raw-corpus accounting remains in `verification.md`.

`.github/workflows/release-rust.yml` runs **only when a `rust-v*` tag is pushed**:

1. Require a clean checkout, exact tag/version/changelog agreement, and a tagged
   commit reachable from `origin/main`.
2. Run the complete reusable verification workflow. Every matrix job must pass.
3. Download the Linux MSRV artifact produced by that same workflow run. Recheck
   the event commit, current tag, source, shared inputs, toolchain and digest.
4. Rebuild the archive with the exact `rust-toolchain.toml` compiler and require
   byte-identical SHA-256 **before** giving Cargo the publishing credential.
5. Check crates.io. An absent version can be published; an existing version must
   have the same checksum and must not be yanked. Authentication errors, rate
   limits, outages and malformed responses are errors, not evidence of absence.
6. Publish with Cargo, check the regenerated archive and public registry digest,
   then install/run the consumer through crates.io using a fresh Cargo home.
   Bounded backoff handles API/index propagation and transient consumer-install
   failures; the upload itself is never retried automatically.
7. Create a Rust-specific GitHub release containing the archive, release record,
   public-installation evidence and checksums. Existing matching releases are
   no-ops; mismatched title, notes, prerelease state, asset names or bytes fail
   without overwriting the release.

"No overwrite" is a policy enforced by this workflow, **not a claim of GitHub's
platform-enforced immutable-release feature**. That repository-wide feature has
not been enabled as part of this Rust-only change, because it could affect the
other ports. Releases are created with `--latest=false` to avoid replacing the
repository's cross-language default release. The checksum/source identity pins
what was verified even if a repository administrator later changes a release.

Cargo does not offer a stable prebuilt-archive upload flag. It repackages at
publication. The pipeline therefore enforces an immutable clean source and pinned
toolchain, checks reproducibility before upload, and verifies Cargo's output and
the registry checksum afterward. It does not claim to have bypassed Cargo's
packager. `--no-verify` is used only for the credential-bearing upload invocation:
the package was already built and consumed without credentials. Compiler and
consumer children do not receive the publishing token.

Stable is a moving compatibility check; it is **not** the release packaging
toolchain. Only the pinned Linux MSRV archive is selected for publication.
Dependencies are resolved with the checked-in lockfile and `--locked`. Repeating
the same release does not silently overwrite a registry version or release asset.

## Authentication and authority

The GitHub environment is **`crates-io`**, restricted to tags matching `rust-v*`.
It holds the encrypted environment secret **`CARGO_REGISTRY_TOKEN`**. Only the
publishing step references it; fork/PR checks and the reusable verification
workflow do not inherit secrets. The token is passed in an environment variable,
never in command-line arguments, Cargo login files, source or artifacts.

Use a crates.io token with only the needed create/publish permissions and restrict
it to the intended crate where the registry permits. It must be able to create
`ftms` for the first publication. Storing a secret in GitHub proves neither token
validity nor registry publish authorization; those remain unverified until an
authorized publication. A dry run does not prove an authenticated upload works.

The supplied token is approved for this publishing process and is configured in
the environment secret. Rotation is not a release prerequisite. If the maintainer
chooses to replace it later, manage the secret in the repository's
**Settings → Environments → crates-io → Environment secrets**:

<https://github.com/deancochran/ftms/settings/environments>

No `cargo login` is required on the runner. Trusted Publishing can replace the
secret in a separate, explicitly configured migration; this workflow uses the requested
token-based authentication rather than claiming OIDC is configured.

The workflow does not create/push Git commits or tags and does not publish from
a manual verification dispatch. Merging the reviewed implementation and pushing
its release tag is the explicit release decision. The environment currently has
no extra manual reviewer gate: a valid tag push triggers the automated gates.

## Preparing a release

1. Complete the intended scope; review public interfaces, crate name, version,
   changelog, docs and supported-toolchain claims. Publication is permanent.
2. Commit and integrate into `main`, preserving the other ports' release paths.
   Confirm the Rust CI jobs on the integrated source pass.
3. With release authority, create and push `rust-vVERSION` at that exact commit.
   The workflow performs publication and creates the GitHub release; no manual
   `cargo publish` command is part of the normal release process.
4. Inspect the workflow's registry consumer and release evidence. Verify the
   crates.io listing and docs.rs documentation separately. docs.rs may build
   asynchronously; it is not one of this workflow's tested consumers.

If a job fails after upload, **do not move the tag or attempt to overwrite the
version**. Rerun the workflow at the same commit. It accepts the published version
only if its checksum matches. A conflicting/yanked version or conflicting GitHub
asset requires investigation and, where appropriate, a new reviewed version.

## Local verification (no publication)

Use Python **3.12+** and the Rust toolchain environment documented in the README.
The publishing tools are package-owned and excluded from the distributed crate.

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
cargo fmt --check
rustfmt --check --edition 2021 tests/fixtures/consumer.rs
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
cargo build --locked --target thumbv6m-none-eabi
RUSTDOCFLAGS='-D warnings' cargo doc --locked --no-deps
python3 scripts/release.py prepare
```

`prepare` deliberately requires clean source. During development only, pass
`--allow-dirty` to build/test a candidate. Its record and archive are marked dirty
and cannot pass the publishing gates. Output stays in the ignored package target
directory. Set `TMPDIR` to a writable temporary directory when necessary.

For an already prepared archive:

```sh
python3 scripts/consumer.py --archive target/distribution/ftms-0.1.0.crate
```

`tests/consumer.sh` remains a local convenience wrapper; it permits a dirty
candidate but never publishes. Release-policy tests use temporary files and mocked
Git/network/Cargo operations; they do not create Git commits or upload packages.

## Setup evidence (before integration)

At initial setup the GitHub environment/tag restriction and encrypted secret were
configured, while the workflow/source changes were local and uncommitted. No Rust
tag, GitHub release or crates.io version was created during setup. Integration
and a release still require explicit authorization. Local Linux checks are
distinct from actual remote CI execution, macOS/Windows results and a real
authenticated registry publication; inspect the tagged workflow's evidence for
those later outcomes rather than treating this setup record as release evidence.
