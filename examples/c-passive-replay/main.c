/* Offline Indoor Bike Data replay. No Bluetooth, transport or control writes. */
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include "ftms/measurement.h"

static int digit(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}
int main(int argc, char **argv) {
  uint8_t bytes[512];
  size_t length, i;
  ftms_measurement value;
  ftms_measurement_format_options format = {
    FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE, FTMS_TREADMILL_PACE_UINT16
  };
  ftms_result result;
  if (argc < 2 || argc > 3) {
    fputs("usage: ftms_passive_replay HEX [uint8Whole|signed16Tenths]\n", stderr);
    return 64;
  }
  if (argc == 3) {
    if (strcmp(argv[2], "signed16Tenths") == 0)
      format.resistance_format = FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS;
    else if (strcmp(argv[2], "uint8Whole") != 0) {
      fputs("unknown explicit resistance format\n", stderr); return 64;
    }
  }
  length = strlen(argv[1]);
  if (length % 2U || length / 2U > sizeof bytes) {
    fputs("expected even hex length, at most 512 bytes\n", stderr); return 64;
  }
  for (i = 0; i < length / 2U; ++i) {
    int high = digit(argv[1][2U * i]), low = digit(argv[1][2U * i + 1U]);
    if (high < 0 || low < 0) { fputs("invalid hex\n", stderr); return 64; }
    bytes[i] = (uint8_t)((unsigned)high * 16U + (unsigned)low);
  }
  result = ftms_decode_measurement_with_format(FTMS_MEASUREMENT_INDOOR_BIKE,
    bytes, length / 2U, &format, &value);
  if (result != FTMS_OK) {
    printf("{\"error\":%d}\n", (int)result); return 2;
  }
  printf("{\"flags\":%" PRIu32 ",\"present\":%" PRIu64
    ",\"unavailable\":%" PRIu64 ",\"moreData\":%u,\"truncated\":%u,"
    "\"trailingBytes\":%u,\"reservedFlags\":%u,\"bytesRead\":%lu,\"values\":[",
    value.flags, value.present, value.unavailable, (unsigned)value.more_data,
    (unsigned)value.truncated, (unsigned)value.trailing_bytes,
    (unsigned)value.reserved_flags, (unsigned long)value.bytes_read);
  for (i = 0; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i)
    printf("%s%" PRId32, i ? "," : "", value.value[i]);
  puts("]}");
  /* Complete transport input can still contain malformed protocol evidence. */
  return value.truncated || value.trailing_bytes || value.reserved_flags ? 2 : 0;
}
