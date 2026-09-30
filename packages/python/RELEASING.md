# Python alpha release

Publishing requires explicit authorization. The distribution is `deancochran-ftms`;
`pyproject.toml` defines its independently versioned Python release. The current
`0.1.0a1` is a partial alpha, not full cross-language API parity or device evidence.

## One-time Trusted Publishing setup

At <https://pypi.org/manage/account/publishing/>, add a **pending publisher**
(the first successful upload creates the project):

| Field | Value |
| --- | --- |
| PyPI project name | `deancochran-ftms` |
| GitHub owner | `deancochran` |
| Repository | `ftms` |
| Workflow filename | `release-python.yml` |
| Environment | `pypi` |

The GitHub repository's `pypi` environment must permit only `python-v*` **tags**
and require approval by `deancochran` before publishing. Repository administrators
must not bypass that approval. Tag restrictions alone are not an approval gate.
No long-lived PyPI token or GitHub secret is needed. Registering a pending
publisher does not reserve the package name or publish anything.

## Authorized release procedure

1. Verify the scope, changelog, version and documentation. Keep capability
   interpretation and other unimplemented APIs explicitly outside this alpha.
2. Commit the reviewed source. From a clean checkout at that exact commit,
   run `uv run --locked --group dev python scripts/verify.py` in `packages/python/`.
   Inspect reports, source identity, clean state and archive contents. Then run:
   `uv tool run --from twine==7.0.0 twine check --strict build/isolated/*.whl build/isolated/*.tar.gz`.
3. Push the source branch and require the Python workflow's verification job to
   pass. A branch push or pull request cannot execute the publishing job.
4. Confirm the PyPI publisher setup and explicit release authorization before
   creating and pushing the immutable `python-vVERSION` tag at that reviewed
   commit. Python tags are independent of `v*` (npm) and `c-v*` tags.
   The initial alpha can be tagged on the reviewed Python branch; this does not
   merge that branch to `main` or authorize merging other ports.
5. The tag workflow verifies the version/tag match, both test interpreters,
   all scoped codec corpora, the structural matrix, and the isolated rebuilt-wheel
   consumer. It checks metadata and saves distributions plus identity/hash reports.
6. Approve the publishing deployment only after reviewing that exact tag/commit
   and its verification job. A separate job, restricted to the `pypi` environment, checks the distribution
   hashes and publishes those exact artifacts using OIDC and attestations. Only
   this job receives `id-token: write`; it does not check out or build source.
7. After publication, the `verify-public` job queries the exact PyPI version,
   requires exactly the expected wheel and source distribution, compares both
   public SHA-256 digests and downloaded bytes to the verified build outputs, and
   executes fresh isolated consumers of both public artifacts. Inspect its retained
   `public-package-verification-report.json` before describing the version as
   published. The same check can be rerun manually with
   `scripts/verify_public.py` and the two digests from the tag workflow.

The workflow deliberately fails on duplicate uploads; do not overwrite or move a
release tag. On a partial upload or network failure, inspect PyPI and compare
existing artifact digests before deciding how to recover. Never bypass a failed
verification gate or claim publication from a pushed tag alone.

The source archive is installable without shared fixtures. Full repository
verification requires a checkout containing the canonical `shared/conformance/`
assets. The package verifier asserts identical wheel bytes after an extracted-sdist
rebuild; it does not claim byte-identical source archives after that rebuild.
