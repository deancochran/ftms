# Releasing Swift in the existing FTMS repository

Swift versions use `packages/swift/VERSION` and **`swift-vVERSION`** tags. They do
not change npm's `v*` tags, C's `c-v*` tags, other package versions, or shared corpus
versions. This deliberately requires SwiftPM **revision/tag pins**, not semantic
version ranges. Do not create another repository as part of this procedure.

Only perform Git commits, pushes, merges and publication with user authorization.

1. Update VERSION and CHANGELOG. Run `Verification/verify.py` with Swift 6.0+ and
   the pinned `requirements-test.txt` validator. Inspect status/diff and the report.
2. Push the candidate branch and open a PR. Require successful existing regression
   CI, Linux/macOS native Swift tests, and the Git consumer's iOS/tvOS/watchOS/
   visionOS SDK builds. No successful workflow is a substitute for reading its
   evidence. Merge only after the final candidate checks pass.
3. Check the actual merged commit and successful `main` checks. Create an annotated
   `swift-vVERSION` tag at that commit and push that tag (never a broad tag push).
4. `Release Swift` reruns Linux/macOS tests and fresh public **tag-pinned** consumers.
   The publishing job requires a clean tag on `main`, matching VERSION/CHANGELOG,
   matching source and fixture hashes, 282 fully accounted-for fixture IDs, and
   all five Apple SDK builds. It creates a non-latest GitHub release with reports
   and SHA256SUMS; npm/C publishing workflows are not triggered by `swift-v*`.
5. Download the public evidence, check its checksums and source identity, and run
   `consumer.py` from an independent consumer against the public tag again:

   ```sh
   python3 packages/swift/Verification/consumer.py \
     --revision swift-v0.1.0 --expected-commit <full-release-commit>
   # On macOS with Xcode selected, append --apple for SDK builds.
   ```

6. Record the release URL, tag/commit, workflow results and installation evidence
   in `docs/released-packages.md`. Keep qualification and real-device evidence
   separate. If any gate fails, fix the candidate before tagging; never move a
   published tag or silently replace an asset. A failed unpublished release run
   can be rerun only after its root cause is understood.

Package-manager consumption comes directly from the Git tag; attached JSON files
are verification evidence, not another package distribution. GitHub also offers
source snapshots. The Swift source remains under `packages/swift/` with a thin
repository-root `Package.swift`.
