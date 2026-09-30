# Independent Dart releases

Publication is a separately authorized external action. Do not publish a
placeholder, reserve a name with empty code, push tags or configure an account
merely because local verification passes.

Identity: `pubspec.yaml` is authoritative; tags are `dart-vVERSION`, independent
of npm, Swift, Kotlin, Python, Rust, FTMS and corpus versions. Initially this is
an **unpublished 0.1.0 candidate**. No package name or publisher is reserved here.

## Release gate

1. Approve the interface, changelog, package name and support/toolchain matrix.
2. Run every Dart CI job, including minimum/current SDK, Linux/macOS/Windows,
   browser JS/Wasm and isolated Flutter Android/iOS builds. Record missing jobs
   as missing evidence, not success. Separately approve committing/integration.
3. At a clean commit on main, approve creation/push of `dart-vVERSION`. The exact
   tag must match the manifest and changelog and be an ancestor of `origin/main`.
4. `python3 tool/release.py prepare --tag dart-vVERSION` reruns the full VM,
   schema, docs, deterministic archive and isolated consumer checks. Inspect
   `build/distribution/package-verification.json` and pub's dry-run file list.
5. A maintainer approves the protected publish job. The job validates the exact
   source/corpus/runner/file identities, extracts the verified archive and uses
   `dart pub publish`. No npm publish command or other port release is involved.
6. Public verification fetches the exact pub.dev version, checks its registry
   archive digest, compares every extracted file to the candidate manifest, then
   executes a fresh hosted consumer. A different compressed archive digest from
   the locally built tarball is expected; extracted file contents must match.
7. Record public URL/version, source commit/tag, archive identity, file manifest,
   CI results and evidence limits in the canonical released-package matrix.

Source changes, stale reports, skips, missing drivers, dirty state, tag/version
mismatch and archive/content differences fail closed. A successful upload followed
by failed public verification means **published, verification failed**; do not
attempt to overwrite the version or claim it never published.

## First publication bootstrap

pub.dev currently requires a first manual upload before GitHub OIDC can be enabled:

- Confirm `deancochran_ftms` remains available and the intended Google account.
- After all release gates/approval, extract the verified candidate archive to an
  isolated directory, inspect `dart pub publish --dry-run`, then run the interactive
  `dart pub publish`. The first version must be real verified code.
- Optionally transfer to a verified publisher/domain you control. This is a
  separate account change and must be explicitly approved.
- Enable GitHub publishing in pub.dev Admin for `deancochran/ftms`, pattern
  `dart-v{{version}}`, requiring the **`pub-dev`** GitHub environment.
- Configure that GitHub environment with required reviewers and appropriate tag
  protection. No long-lived publishing credential is needed.

Subsequent tag-push releases use `.github/workflows/release-dart.yml` and the
explicit `publish --execute` action. Its verification dependencies have no
publishing credentials. Local `prepare` and dry runs cannot upload anything.

The workflow has not been run just by adding its source. Account setup, first
publication, live device checks and post-publication verification are pending
until explicitly authorized and actually executed.

References: [pub.dev publishing](https://dart.dev/tools/pub/publishing),
[OIDC automation](https://dart.dev/tools/pub/automated-publishing).
