# Contributing

Contributions that improve correctness, clear integration, and reproducible
evidence are welcome. This is a maintainer-led project; no response-time or
release-schedule guarantee is implied. Read the [roadmap](docs/roadmap.md) before
proposing a new platform or transport layer.

## Set up and verify

Use Node.js 20+ and pnpm 10.33.0 from the repository root:

```sh
pnpm install --frozen-lockfile
pnpm verify
```

This runs lint, TypeScript type checks/tests, a fresh build and packed-artifact
consumers, documentation link/checker tests and a TypeDoc reference build.
The first install/package check may acquire dependencies; the documentation
checks themselves are offline. `pnpm install` installs the existing Lefthook
pre-push test hook. Installation is not authorization to push.

For C, install GCC/G++, Clang/Clang++, `ar`, CMake 3.16+, a build tool and Python 3
with the dependencies in `packages/c/requirements-test.txt` (prefer a virtualenv):

```sh
make -C packages/c test
```

This includes sanitizer tests, corpora, source-artifact and installed C/C++
consumers. `make -C packages/c check-embedded` is optional Cortex-M0 compile-only
evidence—not a linked firmware image or board test. pnpm does not validate C.

## Change ownership and boundaries

- TypeScript source/tests/manifests/build tools: `packages/typescript/`.
- C source/tests/manifests/build tools: `packages/c/`.
- Language-neutral contracts and canonical fixtures: `shared/`.
- Application/transport recipes: `examples/`, outside protocol cores.
- Cross-language documentation checks: `tools/`; root configs orchestrate only.

Do not add BLE, UI frameworks, logging, timers or application session contracts
to protocol packages. TypeScript protocol bytes are `Uint8Array`/`ArrayBuffer`,
not Buffer or base64; relative ESM imports retain `.js` suffixes. C uses native
pointer/count and fixed-point contracts. Do not copy fixtures into ports or
edit generated npm snapshots. Preserve package exports and release boundaries.

## Tests and protocol corrections

Include a minimal failing example and regression test for a behavior change.
Identify characteristic/opcode, bytes, units, applicable public specification
section or erratum, and expected behavior. Distinguish a device quirk from a
normative correction. Follow the [conformance contract](shared/conformance/README.md)
and [versioning policy](docs/versioning.md) before changing canonical fixtures.
Do not redistribute private specification context or private device logs.

## Documentation and examples

Use the [release matrix](docs/released-packages.md) as the current publication
authority. Historical evidence records retain their original identity and must
not be rewritten to imply a new run. Keep examples complete and assert expected
results. The package verifier copies the current TypeScript examples into an
isolated packed-artifact consumer; native verification exercises installed C/C++
examples. Repository links in shipped npm documentation must use public URLs
when their targets are not included in the package.

Run `pnpm docs:check` for links/status checks and `pnpm docs:build` for generated
reference HTML. Generated output is ignored and must not be hand-edited. The
link checker handles inline Markdown destinations, reference definitions and
heading anchors. It does not resolve undefined reference usages, parse arbitrary
HTML, or check remote URL availability.

The private [Astro/Starlight site](site/README.md) consumes these same canonical
documents. Use Node 22.12+ and `pnpm site:verify` for website changes; `pnpm
site:test:browser` exercises the production build after Chromium installation.
Site dependencies and generated output do not enter published protocol packages.

## Reports and delivery

Use issue templates for protocol bugs, integration questions, feature requests,
and sanitized equipment evidence. Security reports follow [SECURITY.md](SECURITY.md).
Equipment reports must distinguish passive observation, simulated behavior and
authorized physical controls. Never run equipment procedures implicitly.

Describe the exact checks run and their limitations. Commit, merge, publish,
deploy, registry submission and live-device testing are separate actions requiring
maintainer authorization; none is implied by a passing test or contribution.
