# C# release prerequisites

Current state: **local unpublished `0.1.0-alpha.1` candidate**. There is no enabled
NuGet publication workflow or configured account/trusted-publishing claim.

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

## Before enabling publication

Explicitly authorize and verify:

- NuGet account ownership and availability of `DeanCochran.Ftms`.
- Account author-signing requirements, if any.
- Signed annotated tag and approved signer identity, matching VERSION/changelog,
  clean source and reviewed main ancestry.
- Protected GitHub `nuget` environment and NuGet Trusted Publishing binding to
  the canonical repository, exact workflow filename, environment and package scope.

The future tag-only publisher should use a commit-pinned `NuGet/login` action and
short-lived OIDC credentials only in its publishing job. Normal PR/main/manual
verification must remain credential-free. The publishing job must consume the
hash-bound artifacts from its verification job, **without rebuilding** them.

## Required public verification

NuGet.org adds a repository signature, changing the `.nupkg` archive bytes. Save
both the uploaded and downloaded whole-file hashes. Verify the public signature
with the official NuGet client and compare exact archive entry payloads, allowing
only the expected root `.signature.p7s` signing change. Reject duplicate entries,
unexpected entries, changed DLLs/metadata and wrong package ID/version.

`verification/verify-package.py` already provides tested payload-manifest and
local-artifact checks. Its signature-entry comparison is **not** cryptographic
signature verification and is not a finished public-release verifier.

Restore and execute an exact-version public `PackageReference` consumer with a
fresh cache, then record NuGet publication and installed-consumer evidence in the
canonical release matrix. Existing versions and upload-conflict retries must be
verified this same way, not accepted through `--skip-duplicate`. Until those gates
and account settings are implemented and approved, do not push a release tag or
describe this package as publicly available.
