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
