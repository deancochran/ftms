# C# release prerequisites

Current state: the tag-only `release-csharp.yml` workflow can publish an authorized
`csharp-vVERSION` tag through the protected `nuget` environment. This document does
not claim that any version is public; inspect NuGet.org and the completed public job.

`VERSION` owns the version; add the matching heading in `CHANGELOG.md`. C# reserves
`csharp-vVERSION`, independent of every other port. Versions must already be
canonical three-component NuGet SemVer with lowercase prerelease labels, no
leading-zero numeric components, Int32 release components and no build metadata.
Both the local readiness command and the pack target validate that rule.

## Local preparation

1. Run `pnpm release:prepare csharp --dry-run` from the repository root. This
   checks metadata only and does not contact a registry.
2. Run the full package verifier and Linux NativeAOT check; inspect all JSON and
   xUnit reports. Source/fixture identities and dirty state must be accurate.
3. Review public interfaces and dependency metadata. The initial pack validates
   cross-target compatibility; a previous-version API baseline must be deliberately
   configured once a package has been released.
4. Obtain authorization to commit/integrate the source, then repeat the gate from
   the exact clean release commit. Never publish this dirty development artifact.

Regular verification rebuilds ignored `artifacts/`. Archive authorized release
evidence durably before another run; these local outputs are not registry receipts.

## Release contract

Trusted Publishing is bound to `deancochran/ftms`,
`.github/workflows/release-csharp.yml`, the `nuget` environment, and the
`DeanCochran.Ftms` package scope. `NUGET_USER` is an environment variable; the
workflow uses OIDC via the pinned `NuGet/login` action and never stores an API key.

`CSHARP_RELEASE_SIGNER` is a repository Actions variable containing the approved SSH
public-key type and base64. The gate synthesizes an allowed-signers file for principal
`deancochran`, namespace `git`, and requires `git verify-tag`. It rejects
lightweight/unsigned tags, wrong tag/version/changelog, unclean source, a nonmatching
target, and targets outside `origin/main`. After integration, create the tag with:

```sh
git -c gpg.format=ssh -c user.signingkey=~/.ssh/id_ed25519.pub tag -s csharp-vVERSION
```

Normal native C# CI remains credential-free and reusable across Linux, macOS and
Windows. The release gate runs the full verifier plus Linux NativeAOT once, then
uploads exactly one main package, one symbols package, and an SHA-256/size/source
identity manifest. The publish job downloads and validates it; it never rebuilds and
does not use `--skip-duplicate`.

## Required public verification

NuGet.org adds a repository signature, changing the `.nupkg` archive bytes. Save
both the uploaded and downloaded whole-file hashes. Verify the public signature
with the official NuGet client and compare exact archive entry payloads, allowing
only the expected root `.signature.p7s` signing change. Reject duplicate entries,
unexpected entries, changed DLLs/metadata and wrong package ID/version.

The public job calls `dotnet nuget verify --all` with the explicitly pinned current
NuGet.org repository certificate
`1F4B311D9ACC115C8DC8018B5A49E00FCE6DA8E2855F9F014CA6F34570BC482D` and requires
its output to name the NuGet.org repository service index, then compares payload manifests. Whole-file
hashes intentionally differ because NuGet adds `.signature.p7s`; only that root entry
may differ. It retries only 404/transient retrieval failures, restores exact-version
fresh-cache consumers for both TFMs, and writes a separate public report.

The initial package is expected to be NuGet repository-primary signed. If author
signing is enabled later, deliberately extend this policy with the approved author
certificate pin and validation contract; do not assume the repository pin validates
an author-primary package merely because it has a NuGet countersignature.

Restore and execute exact-version public `PackageReference` consumers with fresh
caches, then record NuGet publication and installed-consumer evidence in the canonical
release matrix. Existing versions are checked for payload identity rather than hidden
with `--skip-duplicate`. The `.snupkg` is submitted, but registry symbol indexing is
asynchronous; the workflow does not claim public symbol receipt.
