/* Host-only streaming oracle consumer. Expected fields come from the separate
 * reviewed matrix contract, never the production layout tables. */
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include "ftms/measurement.h"

static void same(const ftms_measurement *a, const ftms_measurement *b) {
  size_t i;
  assert(a->kind == b->kind && a->flags == b->flags);
  assert(a->present == b->present && a->unavailable == b->unavailable);
  for (i = 0; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i) assert(a->value[i] == b->value[i]);
  assert(a->more_data == (b->flags & 1U));
  assert(a->backward == (b->kind == FTMS_MEASUREMENT_CROSS_TRAINER ? ((b->flags >> 15) & 1U) : 0U));
  assert(!a->truncated && !a->trailing_bytes && a->reserved_flags == b->reserved_flags);
}
int main(void) {
  unsigned kind, resistance, pace, rfu, min_budget;
  size_t size, i, count = 0, budgets = 0;
  ftms_measurement expected, actual;
  char hex[129];
  while (scanf("%u %u %u %u %u %zu", &kind, &resistance, &pace, &rfu, &min_budget, &size) == 6) {
    uint8_t input[64], output[64]; size_t written;
    ftms_measurement_format_options options;
    assert(kind < 6 && resistance < 2 && pace < 2 && size <= 64 && rfu < 2);
    memset(&expected, 0, sizeof expected);
    options.resistance_format = (ftms_measurement_resistance_format)resistance;
    options.treadmill_pace_format = (ftms_treadmill_pace_format)pace;
    expected.kind = (ftms_measurement_kind)kind;
    expected.reserved_flags = (uint8_t)rfu;
    assert(scanf("%" SCNu32 " %" SCNu64 " %" SCNu64, &expected.flags, &expected.present, &expected.unavailable) == 3);
    for (i = 0; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i) assert(scanf("%" SCNd32, &expected.value[i]) == 1);
    assert(scanf("%128s", hex) == 1 && strlen(hex) == size * 2U);
    for (i = 0; i < size; ++i) { unsigned byte; assert(sscanf(hex + 2U * i, "%2x", &byte) == 1); input[i] = (uint8_t)byte; }
    assert(ftms_decode_measurement_with_format(expected.kind, input, size, &options, &actual) == FTMS_OK);
    same(&actual, &expected); assert(actual.bytes_read == size);
    if (rfu) assert(ftms_encode_measurement_with_format(&expected, &options, output, sizeof output, &written) == FTMS_ERROR_RANGE);
    else {
      assert(ftms_encode_measurement_with_format(&expected, &options, output, sizeof output, &written) == FTMS_OK);
      assert(written == size && memcmp(input, output, size) == 0);
    }
    if (min_budget) {
      size_t budget;
      /* Every incomplete prefix, including explicit alternative layouts. */
      for (i = 0; i < size; ++i) {
        ftms_result result = ftms_decode_measurement_with_format(expected.kind, input, i, &options, &actual);
        if (i < (kind == 1U ? 3U : 2U)) assert(result == FTMS_ERROR_LENGTH);
        else assert(result == FTMS_OK && actual.truncated && actual.bytes_read <= i);
      }
      for (budget = 0; budget <= 64; ++budget) {
        ftms_measurement_packet packets[FTMS_MEASUREMENT_PLAN_MAX_PACKETS];
        ftms_record_format_context context;
        size_t n = 999, query = 999, j;
        ftms_result result = ftms_measurement_plan_with_format(&expected, &options, budget, packets, FTMS_MEASUREMENT_PLAN_MAX_PACKETS, &n);
        if (budget < min_budget) { assert(result == FTMS_ERROR_LENGTH && n == 999); }
        else {
          assert(result == FTMS_OK && n > 0 && n <= FTMS_MEASUREMENT_PLAN_MAX_PACKETS);
          assert(ftms_measurement_plan_with_format(&expected, &options, budget, NULL, 0, &query) == FTMS_OK && query == n);
          assert(ftms_record_init_with_format(&context, expected.kind, &options, 1, 100) != FTMS_RECORD_INVALID);
          for (j = 0; j < n; ++j) {
            ftms_record_status status;
            assert(packets[j].length <= budget && packets[j].length <= 64);
            status = ftms_record_feed_with_format(&context, packets[j].value, packets[j].length, 1, (uint32_t)j, &actual);
            assert(status == (j + 1 == n ? FTMS_RECORD_COMPLETE : FTMS_RECORD_PENDING));
          }
          same(&actual, &expected);
        }
        budgets++;
      }
    }
    count++;
  }
  assert(feof(stdin) && count == 181863 && budgets == 650);
  printf("Measurement matrix: %zu exact decode/encode cases; %zu planner budgets passed\n", count, budgets);
  return 0;
}
