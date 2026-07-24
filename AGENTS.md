# FTMS package boundary

`@deancochran/ftms` is pure protocol/domain code. It accepts only `Uint8Array`/`ArrayBuffer`; do not add BLE, React Native, Buffer, timers, logging, or app contracts. Keep Node ESM relative imports suffixed with `.js` and verify with `pnpm check-types`, `pnpm test`, `pnpm build`, and `pnpm verify:package`.
