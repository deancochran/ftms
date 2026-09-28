/* Host-only raw measurement bridge; it deliberately has no JSON parser. */
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ftms/measurement.h"

static int number(const char *s, int64_t low, int64_t high, int64_t *out) {
  char *end; long long value;
  errno = 0; value = strtoll(s, &end, 10);
  if (errno || end == s || *end || value < low || value > high) return 0;
  *out = (int64_t)value; return 1;
}
static int nibble(char c) { if (c >= '0' && c <= '9') return c - '0'; if (c >= 'a' && c <= 'f') return c - 'a' + 10; if (c >= 'A' && c <= 'F') return c - 'A' + 10; return -1; }
static int bytes_in(const char *s, uint8_t *out, size_t *size) {
  size_t i, n = strlen(s); if (n % 2U || n > 2048U) return 0;
  for (i = 0; i < n / 2U; ++i) { int a = nibble(s[i * 2U]), b = nibble(s[i * 2U + 1U]); if (a < 0 || b < 0) return 0; out[i] = (uint8_t)((unsigned)a * 16U + (unsigned)b); }
  *size = n / 2U; return 1;
}
static int kind_in(const char *s, ftms_measurement_kind *out) { int64_t n; if (!number(s, INT32_MIN, INT32_MAX, &n)) return 0; *out = (ftms_measurement_kind)n; return 1; }
static void emit(const ftms_measurement *m) {
  size_t i; printf("{\"kind\":%u,\"flags\":%" PRIu32 ",\"present\":%" PRIu64 ",\"unavailable\":%" PRIu64 ",\"values\":[", (unsigned)m->kind, m->flags, m->present, m->unavailable);
  for (i = 0; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i) printf("%s%" PRId32, i ? "," : "", m->value[i]);
  printf("],\"moreData\":%u,\"backward\":%u,\"truncated\":%u,\"trailingBytes\":%u,\"reservedFlags\":%u,\"bytesRead\":%zu}\n", (unsigned)m->more_data, (unsigned)m->backward, (unsigned)m->truncated, (unsigned)m->trailing_bytes, (unsigned)m->reserved_flags, m->bytes_read);
}
static void emit_bytes(const uint8_t *p, size_t n) { size_t i; printf("{\"bytes\":\""); for (i = 0; i < n; ++i) printf("%02x", (unsigned)p[i]); puts("\"}"); }
int main(int argc, char **argv) {
  uint8_t bytes[1024]; size_t size, written; ftms_measurement_kind kind; ftms_result result;
  ftms_measurement_format_options format;
  const ftms_measurement_format_options *options = NULL;
  if (argc < 2) return 64;
  if (!strcmp(argv[1], "decode")) {
    ftms_measurement m;
    if (argc == 6) {
      int64_t resistance, pace;
      if (!number(argv[4], 0, 1, &resistance) || !number(argv[5], 0, 1, &pace)) { puts("{\"bridgeError\":true}"); return 0; }
      format.resistance_format = (ftms_measurement_resistance_format)resistance;
      format.treadmill_pace_format = (ftms_treadmill_pace_format)pace;
      options = &format;
    } else if (argc != 4) { puts("{\"bridgeError\":true}"); return 0; }
    if (!kind_in(argv[2], &kind) || !bytes_in(argv[3], bytes, &size)) { puts("{\"bridgeError\":true}"); return 0; }
    result = ftms_decode_measurement_with_format(kind, bytes, size, options, &m); if (result == FTMS_OK) emit(&m); else printf("{\"error\":%d}\n", (int)result);
  } else if (!strcmp(argv[1], "encode")) {
    ftms_measurement m = {0}; int64_t n; size_t i;
    if (argc == 38) {
      int64_t resistance, pace;
      if (!number(argv[36], 0, 1, &resistance) || !number(argv[37], 0, 1, &pace)) { puts("{\"bridgeError\":true}"); return 0; }
      format.resistance_format = (ftms_measurement_resistance_format)resistance;
      format.treadmill_pace_format = (ftms_treadmill_pace_format)pace;
      options = &format;
    } else if (argc != 36) { puts("{\"bridgeError\":true}"); return 0; }
    if (!kind_in(argv[2], &kind) || !number(argv[3], 0, UINT32_MAX, &n)) { puts("{\"bridgeError\":true}"); return 0; }
    m.kind = kind; m.flags = (uint32_t)n;
    if (!number(argv[4], 0, INT64_C(1073741823), &n)) { puts("{\"bridgeError\":true}"); return 0; } m.present = (uint64_t)n;
    if (!number(argv[5], 0, INT64_C(1073741823), &n)) { puts("{\"bridgeError\":true}"); return 0; } m.unavailable = (uint64_t)n;
    for (i = 0; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i) { if (!number(argv[i + 6U], INT32_MIN, INT32_MAX, &n)) { puts("{\"bridgeError\":true}"); return 0; } m.value[i] = (int32_t)n; }
    result = ftms_encode_measurement_with_format(&m, options, bytes, sizeof bytes, &written); if (result == FTMS_OK) emit_bytes(bytes, written); else printf("{\"error\":%d}\n", (int)result);
  } else return 64;
  return 0;
}
