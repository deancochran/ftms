# FTMS package boundary

`@deancochran/ftms` is pure protocol/domain code. It accepts only `Uint8Array`/`ArrayBuffer`; do not add BLE, React Native, Buffer, timers, logging, or app contracts. Keep Node ESM relative imports suffixed with `.js` and verify with `pnpm check-types`, `pnpm test`, `pnpm build`, and `pnpm verify:package`.

The complete adopted Fitness Machine Service 1.0 specification is available as local-only project context at `.context/ftms/fitness-machine-service-1.0.txt` (with the source PDF alongside it). Consult it for protocol semantics; apply mandatory Errata Correction 23224 where it supersedes the adopted text.
