# Go verification

## Repeatable commands

Run from `packages/go`. Ordinary package tests are standard-library-only:

```sh
go vet ./...
go test -race ./...
go build ./...
go test -run='^$' -fuzz=FuzzDecodeWire -fuzztime=10s
go test -run='^$' -fuzz=FuzzInterpretCapabilities -fuzztime=10s
```

Use a contributor virtual environment for the schema validator when needed:

```sh
python3 -m venv "$HOME/.cache/ftms-go-venv"
source "$HOME/.cache/ftms-go-venv/bin/activate"
python3 -m pip install -r scripts/requirements.txt
bash scripts/verify.sh
```

`verify.sh` checks formatting, canonical license equality, five exact JSON schemas
using `jsonschema==4.26.0`, unique case IDs, vet, race tests, all currently supported
conformance contracts, compilation, and an isolated consumer. Schema validation
disallows automatic remote reference retrieval. Python is contributor tooling,
not a runtime or installed-consumer dependency.

The direct `go test -tags conformance ./...` command validates capability source
and expanded-fixture schemas through a package-owned Python helper. It does not
validate the five raw additive JSON Schemas by itself; those reports explicitly
require the separate schema gate. Do not present direct Go test output alone as
schema validation for the raw corpora.

Reports default to `$XDG_CACHE_HOME/ftms-go-reports`, or
`$HOME/.cache/ftms-go-reports`; override with `FTMS_GO_REPORT_DIR`. Outputs include:

- `schema-validation.json`: schema validation and SHA-256 identities.
- `conformance.json`: source HEAD/dirty state, Go toolchain, each additive case
  and direction, hashes, counts, failures, unsupported and skipped totals.
- `conformance.log`: detailed Go outcomes, inspection identities, structural
  matrix identities and accounting.
- `capabilities.json`: complete capability-case accounting, category counts,
  each outcome and non-pass reason, schema identity and specification basis,
  source HEAD/dirty state, actual Go toolchain, and SHA-256 of the capability
  schema, vectors, comparison README, and protocol contract. `complete` is true
  only for a nonempty fully executed run with zero failures/skips/unsupported.
- `capability-fixtures.log`: strict template-expansion and schema-negative tests.
- `consumer.log`: installed-module tests/build, isolated executable consumer,
  local-only module zip checksum and module identity.

Fixture/schema errors, missing assets, duplicate IDs, failed comparisons, and
driver failures are failures, not skips. The matrix and inspection contracts
have no JSON Schema file; their local contract structure and identities are
checked separately. See `coverage.md` for exact scope exclusions.

Capability fixtures expand only literal data: independent deep copies for input
and expectation; ordered replace/append/remove edits; strict existing keys and
indices; wildcard and distinct-index selections for replace only. Neither
expected reports nor expansion logic call any protocol implementation. The Go
runner invokes the actual library and compares entire normalized reports with
exact key sets, ordered arrays, integer/string/null values and types. An invalid
fixture/runner writes an incomplete failure report instead of leaving a stale
successful capability report. The pinned Python tools are only needed for
checkout conformance, never for ordinary installed-module use.

## Consumer packaging

`python3 scripts/verify-consumer.py` constructs a source-module zip with the
required path prefix and serves it through a local `file://` Go proxy. A new
consumer with a fresh module cache downloads `v0.0.0-local`, checks module sums,
and runs telemetry/request/capability code. It also tests a separate copy of the downloaded
module without the checkout's shared fixtures.

There is no `replace` directive, no `go.work`, and no public request. `GOSUMDB=off`
is limited to this synthetic local proxy gate. Public release verification must
use the normal checksum database instead. A local zip proves local packaging,
not a public tag, Go proxy availability, or pkg.go.dev indexing.

## Toolchains and evidence limits

The module declares Go 1.24. CI is configured for Go 1.24.x and 1.27.x on Linux;
workflow configuration is not evidence that hosted CI ran. Local compiler/test
results must report the actual Go version used. Other operating systems and
architectures require their own executed evidence before support claims.

Fuzzing is bounded and checks malformed input, decoder input immutability, and
consumed offsets across measurement families and explicit formats. Passing a
bounded fuzz run is not a proof of absence of bugs. This package's checks do not
replace hardware, transport, or qualification testing. Root `pnpm verify` does
not validate Go.
