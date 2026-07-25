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
