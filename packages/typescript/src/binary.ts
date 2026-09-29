import { RawCodecError } from "./types.js";

/** Explicit configuration cannot come from inherited fields or getters.
 * Accepts foreign-realm/null-prototype objects; not a sandbox for hostile Proxies. */
export function validateOwnSettings(
  value: unknown,
  fields: readonly string[],
  allowOtherFields = false,
): void {
  if (value === undefined) return;
  if (value === null || typeof value !== "object" || Array.isArray(value))
    throw new RawCodecError("kind", "Settings must be an options object");
  if (
    !allowOtherFields &&
    Reflect.ownKeys(value).some((key) => typeof key !== "string" || !fields.includes(key))
  )
    throw new RawCodecError("kind", "Unknown settings field");
  for (const field of fields) {
    const descriptor = Object.getOwnPropertyDescriptor(value, field);
    if (descriptor ? !("value" in descriptor) : field in value)
      throw new RawCodecError("kind", `${field} must be an own data property`);
  }
}

/** Realm-safe check for the only byte containers accepted by the public API. */
export function isByteSource(data: unknown): data is ArrayBuffer | Uint8Array {
  if (ArrayBuffer.isView(data)) {
    // The intrinsic getter reads typed-array internal slots, not a forgeable
    // instance Symbol.toStringTag (Uint16Array can override that property).
    const tag = Object.getOwnPropertyDescriptor(
      Object.getPrototypeOf(Uint8Array.prototype),
      Symbol.toStringTag,
    )?.get;
    return tag?.call(data) === "Uint8Array";
  }
  try {
    const byteLength = Object.getOwnPropertyDescriptor(ArrayBuffer.prototype, "byteLength")?.get;
    if (!byteLength) return false;
    byteLength.call(data);
    return true;
  } catch {
    return false;
  }
}

export function toDataView(data: ArrayBuffer | Uint8Array): DataView {
  return ArrayBuffer.isView(data)
    ? new DataView(data.buffer, data.byteOffset, data.byteLength)
    : new DataView(data);
}

export function toBytes(data: ArrayBuffer | Uint8Array): Uint8Array {
  return ArrayBuffer.isView(data)
    ? new Uint8Array(data.buffer, data.byteOffset, data.byteLength)
    : new Uint8Array(data);
}
