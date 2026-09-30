# Kotlin release gates

Kotlin is independently versioned. Coordinates are
`io.github.deancochran:ftms:0.1.0`; a local Maven artifact is not a public release.
Kotlin release tags use `kotlin-vVERSION`, never the existing npm `v*` or C `c-v*`
tag namespaces.

## Verification before delivery

1. Run the complete package checks against canonical shared fixtures, including
   schema validation, literal encode/decode expectations, exact report comparisons,
   measurement layout matrix, and invalid-input tests. Record corpus hashes,
   comparison contracts, source commit and dirty state with complete accounting.
2. Run `bash verification/verify.sh` from the package (or invoke it by path from
   the repository). This includes isolated Maven-artifact Kotlin and Java callers
   and an Android APK build. Inspect all outputs, not just a successful compile.
3. Review the public API and package dependencies. Only the Kotlin standard library
   is intended as a runtime dependency; Gson/schema/JUnit dependencies are test-only.
4. Commit the verified source; rerun on the clean commit. Use that immutable commit
   for a release tag and artifacts. Do not alter shared contracts to make tests pass.

## Maven Central prerequisites

Publishing requires a Central Portal account authorized for the
`io.github.deancochran` namespace, a Portal publishing token, and an approved
signing key with its public key available as required by Central. GitHub access
does not imply Central access. Never put tokens or private keys in this repository
or console logs; provision them through a secret store or protected environment.

The release must include the binary, sources, documentation, complete POM metadata
(license, SCM, project and developer identity), signatures and required checksums.
Verify namespace ownership and signing identity rather than inventing either.
Upload only the artifact bytes already tested by isolated consumers. Confirm the
Portal reports `PUBLISHED`, then download and verify the public coordinates and
artifact digests before reporting Maven Central publication.

A GitHub release may distribute verified artifacts, but it must not be described
as Maven Central availability. Never substitute an empty JAR, unsigned placeholder
or incomplete protocol implementation to bypass a publication blocker.

## Standard publishing method

`publishing/publish.py` is the package-owned Central Publisher API client. It uses
Python's standard library and GnuPG, not an unpinned publishing plugin. Ordinary
Gradle builds and CI have no publishing credentials and cannot publish. Each
remote step is explicit; no release occurs automatically on a push or tag.

Requirements: Python 3.10+, GnuPG 2.2+, Git, the JDK/Android SDK used by the
verification script, a clean checkout, and explicit release authorization.

### Machine-local credentials and signing

The default configuration is `~/.config/ftms/publishing/` (directory mode `0700`).
Override with `--config /secure/path` if using a separately provisioned secret
store. This directory must be outside the checkout. Its files are mode `0600`:

| File | Purpose |
| --- | --- |
| `central-token` | Base64 of Portal token username, colon, password; sent only as an HTTPS authorization header |
| `signing-fingerprint` | Full uppercase fingerprint; never a short key ID |
| `signing-passphrase` | Passphrase read by GPG from a file, not a command-line argument |
| `gnupg/` | Dedicated owner-only GPG home containing the encrypted private key |

The first release key was created using the repository's configured author
identity (Dean Cochran, FTMS releases), not a fabricated publisher. Its fingerprint
is **`A355E4B9EBD3FAEC850A84A6B7A6488FE4805547`**. The RSA-4096 signing key has a
two-year validity period. The public key is distributed at
<https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xA355E4B9EBD3FAEC850A84A6B7A6488FE4805547>.
Retain this identity across releases; do not generate a new key per version.

The local configuration also contains encrypted `signing-private.asc`,
`signing-public.asc`, and GPG's revocation certificate under
`gnupg/openpgp-revocs.d/`. Back up the private key and revocation certificate in
an encrypted secret store, with the passphrase managed separately. A second copy
on this machine is not an off-machine recovery backup. Never commit private keys,
passphrases or tokens, or attach them to releases. Renew and redistribute the
public key before expiration; document any deliberate key rotation here.

To provision or replace a Portal token without placing it in shell history or
process arguments, use an interactive prompt (no credential values are printed):

```sh
python3 - <<'PY'
import base64, getpass, os
from pathlib import Path
os.umask(0o077)
directory = Path.home() / '.config/ftms/publishing'
directory.mkdir(parents=True, exist_ok=True, mode=0o700)
directory.chmod(0o700)
username = getpass.getpass('Portal token username: ')
password = getpass.getpass('Portal token password: ')
temporary = directory / 'central-token.new'
with temporary.open('x') as output:
    output.write(base64.b64encode(f'{username}:{password}'.encode()).decode() + '\n')
temporary.replace(directory / 'central-token')
PY
```

Credential checks reject group/world-readable configuration and symlinked secret
files. API errors omit response bodies/headers; authenticated requests reject
redirects. Credentials are never passed to Gradle, consumer builds, GitHub, or
the public Maven download endpoint. Do not run the publisher with shell tracing.

### Release sequence

Run from the repository root. Replace `0.1.0` with the reviewed package version.
The POM generated by Gradle is authoritative for the coordinates and consumer
version; no release step silently selects `latest`.

1. Update the package version/changelog and review the API baseline. Commit and
   push changes, and require the PR's Kotlin, TypeScript and native checks to pass.
   Preserve other ports' versions, release tags and canonical fixtures.
2. Prepare **from that clean commit**:

   ```sh
   ANDROID_HOME=/path/to/android-sdk python3 packages/kotlin/publishing/publish.py prepare
   ```

   This reruns the offline publisher regression tests, full Kotlin conformance
   and API checks, local publication, Kotlin/Java execution and Android APK build.
   It then signs those exact binary/source/documentation JARs, POM and Gradle
   metadata; adds MD5/SHA-1/SHA-256/SHA-512 sidecars; and signs a manifest recording
   the source commit and every bundle-file hash. It performs **no remote upload**.
3. Inspect `.releases/current/` inside the package, including `verification.log`
   and `manifest.json`. Create and push a signed annotated tag identifying that commit:

   ```sh
   GNUPGHOME="$HOME/.config/ftms/publishing/gnupg" git \
     -c gpg.program=gpg -c gpg.format=openpgp \
     -c user.signingkey=A355E4B9EBD3FAEC850A84A6B7A6488FE4805547 \
     tag -s kotlin-v0.1.0 -m 'FTMS Kotlin/JVM 0.1.0'
   git push origin refs/tags/kotlin-v0.1.0
   ```

4. Upload for Central validation only:

   ```sh
   python3 packages/kotlin/publishing/publish.py upload
   ```

   The client checks namespace access, the tag signature and local/remote tag object, clean
   source, the signed manifest, and bundle hashes. It uses `USER_MANAGED`, records
   the deployment ID immediately, and waits for `VALIDATED`. No automatic publish.
5. Publish only the validated deployment, then verify public bytes and consumers:

   ```sh
   python3 packages/kotlin/publishing/publish.py publish
   ANDROID_HOME=/path/to/android-sdk python3 packages/kotlin/publishing/publish.py verify
   ```

   Before the irreversible publish request, the client checks the deployment's
   exact Maven PURL and downloads its staged artifacts/signatures to compare with
   the signed bundle manifest. The saved source commit and tag object must also
   match. `publish` waits for `PUBLISHED`; `verify` downloads the exact coordinates from
   Maven Central, compares all file hashes, verifies OpenPGP signatures and runs
   the isolated Java/Kotlin/Android consumers against that public repository.
   FTMS resolution remains exclusive, and dependency refresh is forced.
6. Record the exact commit, deployment, published artifact hashes and verified
   results in `docs/released-packages.md`. A GitHub release for the same tag may
   attach `central-bundle.zip`, `manifest.json`, `manifest.json.asc`,
   `signing-public.asc`, `central-status.json`, and `public-verification.json`
   from the release directory. A public claim requires both Portal `PUBLISHED`
   **and** successful public verification, not just a successful upload.

### Resume and evidence retention

Release evidence lives at `packages/kotlin/.releases/current/` (Git-ignored and
not removed by Gradle `clean`). Once delivered, archive this directory as
`.releases/kotlin-vVERSION/` before preparing another release. Preparation refuses
to replace existing release evidence. Retain a durable backup of public receipts
and signed manifests, for example the GitHub release assets above.

`upload`, `publish` and `verify` can be resumed from the same prepared commit.
An existing deployment record prevents a second upload; an already-published
deployment is not republished. If an upload's connection fails **before** the
deployment ID is saved, inspect Central's deployment history before retrying—
the server might have accepted it. Never blindly retry an ambiguous upload or
delete failed evidence while investigating. `--timeout SECONDS` controls waiting;
a timeout is not a deployment failure. Public CDN propagation can lag Portal
publication; retry `verify`, not `upload`, when public files are not yet visible.

The client intentionally has no delete/redeploy, automatic version bump, automatic
merge, or credential-upload feature. Published Maven versions are immutable.
CI secrets or a protected publishing workflow can be provisioned separately;
the standard local method does not require changing an external account's secrets.

Tag names must never be moved or reused as a release policy. The client verifies
the signed tag object and remote target at each step; that is not proof of a
GitHub tag-protection rule. No such remote protection setting is established by
this tooling. A repository administrator can separately protect `kotlin-v*`
against deletion/updates. The permanent artifact identity is the immutable source
commit plus signed manifest, not an assumption that a remote ref cannot change.

## Evidence boundaries

JVM conformance, Android packaging, emulator execution and live Bluetooth exchange
are separate evidence. Release checks issue no equipment commands. Recorded
KICKR packets may be replayed offline; that does not imply a new live Kotlin test.

References:

- https://central.sonatype.org/publish/publish-portal-api/
- https://central.sonatype.org/publish/requirements/
- https://kotlinlang.org/docs/api-guidelines-backward-compatibility.html
- https://docs.gradle.org/current/userguide/publishing_maven.html
