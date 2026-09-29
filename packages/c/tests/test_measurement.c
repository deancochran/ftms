#include "ftms/measurement.h"
#include <assert.h>
#include <string.h>

#define BIT(f) (UINT64_C(1) << (f))

static void same_measurement(const ftms_measurement *left, const ftms_measurement *right);

static void one(ftms_measurement_kind kind, uint32_t flags, ftms_measurement_field field,
                int32_t value) {
  ftms_measurement in, decoded;
  uint8_t bytes[64], saved[64]; size_t n = 999U, i;
  size_t flag_bytes = kind == FTMS_MEASUREMENT_CROSS_TRAINER ? 3U : 2U;
  memset(&in, 0, sizeof in); in.kind = kind; in.flags = flags;
  in.present = BIT(field); in.value[field] = value;
  assert(ftms_encode_measurement(&in, bytes, sizeof bytes, &n) == FTMS_OK);
  assert(ftms_decode_measurement(kind, bytes, n, &decoded) == FTMS_OK);
  assert(decoded.present == in.present && decoded.value[field] == value);
  for (i = flag_bytes; i < n; ++i) {
    assert(ftms_decode_measurement(kind, bytes, i, &decoded) == FTMS_OK);
    assert(decoded.truncated != 0U);
  }
  memcpy(saved, bytes, sizeof bytes); n = 77U;
  assert(ftms_encode_measurement(&in, bytes, 0U, &n) == FTMS_ERROR_LENGTH);
  assert(n == 77U && memcmp(bytes, saved, sizeof bytes) == 0);
}

/* Exercise each complete payload's every proper prefix without duplicating corpus bytes. */
static void full_payload_prefixes(ftms_measurement_kind kind, uint32_t flags,
                                  uint64_t present, size_t expected_size) {
  ftms_measurement in, decoded;
  uint8_t bytes[64], saved[64]; size_t n, i;
  const size_t flag_bytes = kind == FTMS_MEASUREMENT_CROSS_TRAINER ? 3U : 2U;
  memset(&in, 0, sizeof in);
  in.kind = kind; in.flags = flags; in.present = present;
  for (i = 0U; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i) in.value[i] = 1;
  assert(ftms_encode_measurement(&in, bytes, sizeof bytes, &n) == FTMS_OK);
  assert(n == expected_size);
  for (i = flag_bytes; i < n; ++i) {
    assert(ftms_decode_measurement(kind, bytes, i, &decoded) == FTMS_OK);
    assert(decoded.truncated != 0U && decoded.bytes_read <= i);
  }
  memcpy(saved, bytes, sizeof bytes); n = 91U;
  assert(ftms_encode_measurement(&in, bytes, expected_size - 1U, &n) == FTMS_ERROR_LENGTH);
  assert(n == 91U && memcmp(bytes, saved, sizeof bytes) == 0);
}

static void invalid_inputs(void) {
  ftms_measurement m, before;
  uint8_t bytes[64] = {0}, saved[64]; size_t written = 44U;
  memset(&m, 0, sizeof m); m.kind = FTMS_MEASUREMENT_INDOOR_BIKE;
  m.present = BIT(FTMS_M_SPEED); m.value[FTMS_M_SPEED] = 1;
  before = m;
  assert(ftms_decode_measurement((ftms_measurement_kind)-1, bytes, 2U, &m) == FTMS_ERROR_KIND);
  assert(memcmp(&m, &before, sizeof m) == 0);
  assert(ftms_decode_measurement((ftms_measurement_kind)256, bytes, 2U, &m) == FTMS_ERROR_KIND);
  assert(ftms_decode_measurement(FTMS_MEASUREMENT_INDOOR_BIKE, NULL, 2U, &m) == FTMS_ERROR_NULL);
  assert(ftms_decode_measurement(FTMS_MEASUREMENT_INDOOR_BIKE, bytes, 2U, NULL) == FTMS_ERROR_NULL);
  assert(ftms_encode_measurement(NULL, bytes, sizeof bytes, &written) == FTMS_ERROR_NULL);
  assert(ftms_encode_measurement(&m, NULL, sizeof bytes, &written) == FTMS_ERROR_NULL);
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, NULL) == FTMS_ERROR_NULL);
  m.kind = (ftms_measurement_kind)-1;
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &written) == FTMS_ERROR_KIND);
  m.kind = (ftms_measurement_kind)256;
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &written) == FTMS_ERROR_KIND);
  m = before; m.present |= BIT(FTMS_M_POWER);
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &written) == FTMS_ERROR_RANGE);
  m = before; m.present = 0U;
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &written) == FTMS_ERROR_RANGE);
  m = before; m.unavailable = BIT(FTMS_M_POWER);
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &written) == FTMS_ERROR_RANGE);
  m = before; m.value[FTMS_M_SPEED] = -1;
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &written) == FTMS_ERROR_RANGE);
  memcpy(saved, bytes, sizeof bytes); assert(written == 44U && memcmp(bytes, saved, sizeof bytes) == 0);
}

static void sentinels_and_overlap(void) {
  ftms_measurement m;
  uint8_t bytes[64], expected[64]; size_t n, expected_n;
  union { ftms_measurement measurement; uint8_t raw[sizeof(ftms_measurement)]; } overlapping;
  /* -32768 is available; +32767 is the signed treadmill unavailable sentinel. */
  memset(&m, 0, sizeof m); m.kind = FTMS_MEASUREMENT_TREADMILL; m.flags = 9U;
  m.present = BIT(FTMS_M_INCLINATION)|BIT(FTMS_M_RAMP_ANGLE);
  m.value[FTMS_M_INCLINATION] = -32768;
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &n) == FTMS_OK);
  assert(ftms_decode_measurement(FTMS_MEASUREMENT_TREADMILL, bytes, n, &m) == FTMS_OK);
  assert(m.value[FTMS_M_INCLINATION] == -32768 && (m.unavailable & BIT(FTMS_M_INCLINATION)) == 0U);
  { uint8_t b[] = {0x09,0x00,0xff,0x7f,0x00,0x00};
    assert(ftms_decode_measurement(FTMS_MEASUREMENT_TREADMILL,b,sizeof b,&m)==FTMS_OK);
    assert((m.unavailable & BIT(FTMS_M_INCLINATION)) != 0U); }
  { uint8_t b[] = {0x00,0x01,0x00,0x00,0xff,0xff,0xff,0xff,0xff};
    assert(ftms_decode_measurement(FTMS_MEASUREMENT_INDOOR_BIKE,b,sizeof b,&m)==FTMS_OK);
    assert((m.unavailable & (BIT(FTMS_M_TOTAL_ENERGY)|BIT(FTMS_M_ENERGY_PER_HOUR)|BIT(FTMS_M_ENERGY_PER_MINUTE))) != 0U); }
  one(FTMS_MEASUREMENT_INDOOR_BIKE, 65U, FTMS_M_POWER, 32767);
  memset(&m, 0, sizeof m); m.kind = FTMS_MEASUREMENT_TREADMILL; m.flags = 4097U;
  m.present = BIT(FTMS_M_FORCE_ON_BELT)|BIT(FTMS_M_POWER); m.value[FTMS_M_POWER] = 32767;
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &n) == FTMS_ERROR_RANGE);
  m.unavailable = BIT(FTMS_M_POWER);
  assert(ftms_encode_measurement(&m, bytes, sizeof bytes, &n) == FTMS_OK);
  /* Staged output permits input/output overlap. */
  memset(&m, 0, sizeof m); m.kind = FTMS_MEASUREMENT_INDOOR_BIKE;
  m.present = BIT(FTMS_M_SPEED); m.value[FTMS_M_SPEED] = 1234;
  assert(ftms_encode_measurement(&m, expected, sizeof expected, &expected_n) == FTMS_OK);
  overlapping.measurement = m;
  assert(ftms_encode_measurement(&overlapping.measurement, overlapping.raw, sizeof overlapping.raw, &n) == FTMS_OK);
  assert(n == expected_n && memcmp(overlapping.raw, expected, n) == 0);
}

static void format_overrides(void) {
  ftms_measurement decoded, input;
  const ftms_measurement_format_options signed_resistance = {
    FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS, FTMS_TREADMILL_PACE_UINT16};
  const ftms_measurement_format_options legacy_pace = {
    FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE, FTMS_TREADMILL_PACE_UINT8_LEGACY};
  const uint8_t resistance[] = {0x60,0x08,0x01,0x00,0x78,0x00,0x2c,0x01,0x85,0x03};
  const uint8_t pace[] = {0x60,0x04,0xe8,0x03,0x2a,0x2b,0x85,0x03};
  uint8_t output[64]; size_t written = 99U;
  assert(ftms_decode_measurement_with_format(FTMS_MEASUREMENT_INDOOR_BIKE,
    resistance, sizeof resistance, &signed_resistance, &decoded) == FTMS_OK);
  assert(decoded.flags == 0x860U && decoded.present == (BIT(FTMS_M_SPEED)|BIT(FTMS_M_RESISTANCE)|BIT(FTMS_M_POWER)|BIT(FTMS_M_ELAPSED_TIME)));
  assert(decoded.value[FTMS_M_RESISTANCE] == 120 && decoded.value[FTMS_M_POWER] == 300 && decoded.value[FTMS_M_ELAPSED_TIME] == 901);
  input = decoded;
  assert(ftms_encode_measurement_with_format(&input, &signed_resistance, output, sizeof output, &written) == FTMS_OK);
  assert(written == sizeof resistance && memcmp(output, resistance, sizeof resistance) == 0);
  { uint8_t saved[64]; const int32_t limits[] = {-32768, 32767}; size_t i;
    for (i = 0U; i < 2U; ++i) {
      input.value[FTMS_M_RESISTANCE] = limits[i];
      assert(ftms_encode_measurement_with_format(&input, &signed_resistance, output, sizeof output, &written) == FTMS_OK);
      assert(output[4] == (i == 0U ? 0U : 255U) && output[5] == (i == 0U ? 128U : 127U));
      assert(ftms_decode_measurement_with_format(input.kind, output, written, &signed_resistance, &decoded) == FTMS_OK);
      assert(decoded.value[FTMS_M_RESISTANCE] == limits[i] && decoded.unavailable == 0U);
    }
    memcpy(saved, output, sizeof saved); written = 99U;
    assert(ftms_encode_measurement_with_format(&input, &signed_resistance, output, 9U, &written) == FTMS_ERROR_LENGTH);
    assert(written == 99U && memcmp(saved, output, sizeof saved) == 0);
    input.value[FTMS_M_RESISTANCE] = 32768;
    assert(ftms_encode_measurement_with_format(&input, &signed_resistance, output, sizeof output, &written) == FTMS_ERROR_RANGE);
    assert(written == 99U && memcmp(saved, output, sizeof saved) == 0);
  }
  assert(ftms_decode_measurement_with_format(FTMS_MEASUREMENT_TREADMILL,
    pace, sizeof pace, &legacy_pace, &decoded) == FTMS_OK);
  assert(decoded.value[FTMS_M_SPEED] == 1000 && decoded.value[FTMS_M_INSTANTANEOUS_PACE] == 42 && decoded.value[FTMS_M_AVERAGE_PACE] == 43 && decoded.value[FTMS_M_ELAPSED_TIME] == 901);
  input = decoded;
  assert(ftms_encode_measurement_with_format(&input, &legacy_pace, output, sizeof output, &written) == FTMS_OK);
  assert(written == sizeof pace && memcmp(output, pace, sizeof pace) == 0);
  { ftms_measurement_format_options bad = {(ftms_measurement_resistance_format)-1, FTMS_TREADMILL_PACE_UINT16};
    decoded = input;
    assert(ftms_decode_measurement_with_format(FTMS_MEASUREMENT_TREADMILL, pace, sizeof pace, &bad, &decoded) == FTMS_ERROR_KIND);
    assert(memcmp(&decoded, &input, sizeof input) == 0);
    assert(ftms_encode_measurement_with_format(&input, &bad, output, sizeof output, &written) == FTMS_ERROR_KIND); }
}

static void formatted_planner_regressions(void) {
  const ftms_measurement_format_options signed_resistance = {
    FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS, FTMS_TREADMILL_PACE_UINT16};
  const ftms_measurement_format_options legacy_pace = {
    FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE, FTMS_TREADMILL_PACE_UINT8_LEGACY};
  ftms_measurement in;
  ftms_measurement_packet packets[FTMS_MEASUREMENT_PLAN_MAX_PACKETS], saved[FTMS_MEASUREMENT_PLAN_MAX_PACKETS];
  size_t count, old, i;
  const uint8_t bike6[][6] = {{0x61,0x00,0x78,0x00,0x2c,0x01}, {0x01,0x08,0x85,0x03}, {0,0,1,0}};
  const size_t bike6n[] = {6U,4U,4U};
  const uint8_t tread4[][4] = {{0x61,0x00,0x2a,0x2b}, {0x01,0x04,0x85,0x03}, {0,0,0xe8,0x03}};
  memset(&in, 0, sizeof in); in.kind = FTMS_MEASUREMENT_INDOOR_BIKE; in.flags = 0x860U;
  in.present = BIT(FTMS_M_SPEED)|BIT(FTMS_M_RESISTANCE)|BIT(FTMS_M_POWER)|BIT(FTMS_M_ELAPSED_TIME);
  in.value[FTMS_M_SPEED] = 1; in.value[FTMS_M_RESISTANCE] = 120; in.value[FTMS_M_POWER] = 300; in.value[FTMS_M_ELAPSED_TIME] = 901;
  assert(ftms_measurement_plan_with_format(&in, &signed_resistance, 6U, NULL, 0U, &count) == FTMS_OK && count == 3U);
  assert(ftms_measurement_plan_with_format(&in, &signed_resistance, 6U, packets, count, &count) == FTMS_OK && count == 3U);
  for (i = 0U; i < count; ++i) assert(packets[i].length == bike6n[i] && memcmp(packets[i].value, bike6[i], bike6n[i]) == 0);
  assert(ftms_measurement_plan_with_format(&in, &signed_resistance, 5U, NULL, 0U, &count) == FTMS_OK && count == 4U);
  assert(ftms_measurement_plan(&in, 5U, NULL, 0U, &count) == FTMS_OK && count == 3U);

  memset(&in, 0, sizeof in); in.kind = FTMS_MEASUREMENT_TREADMILL; in.flags = 0x460U;
  in.present = BIT(FTMS_M_SPEED)|BIT(FTMS_M_INSTANTANEOUS_PACE)|BIT(FTMS_M_AVERAGE_PACE)|BIT(FTMS_M_ELAPSED_TIME);
  in.value[FTMS_M_SPEED] = 1000; in.value[FTMS_M_INSTANTANEOUS_PACE] = 42; in.value[FTMS_M_AVERAGE_PACE] = 43; in.value[FTMS_M_ELAPSED_TIME] = 901;
  assert(ftms_measurement_plan_with_format(&in, &legacy_pace, 4U, NULL, 0U, &count) == FTMS_OK && count == 3U);
  assert(ftms_measurement_plan_with_format(&in, &legacy_pace, 4U, packets, count, &count) == FTMS_OK && count == 3U);
  for (i = 0U; i < count; ++i) assert(packets[i].length == 4U && memcmp(packets[i].value, tread4[i], 4U) == 0);
  assert(ftms_measurement_plan(&in, 4U, NULL, 0U, &count) == FTMS_OK && count == 4U);

  memset(&in, 0, sizeof in); in.kind = FTMS_MEASUREMENT_TREADMILL; in.flags = 0x80U;
  in.present = BIT(FTMS_M_SPEED)|BIT(FTMS_M_TOTAL_ENERGY)|BIT(FTMS_M_ENERGY_PER_HOUR)|BIT(FTMS_M_ENERGY_PER_MINUTE);
  in.value[FTMS_M_SPEED] = 1; in.value[FTMS_M_TOTAL_ENERGY] = 1; in.value[FTMS_M_ENERGY_PER_HOUR] = 1; in.value[FTMS_M_ENERGY_PER_MINUTE] = 1;
  assert(ftms_measurement_plan(&in, 6U, NULL, 0U, &count) == FTMS_ERROR_LENGTH);

  memset(&in, 0, sizeof in); in.kind = FTMS_MEASUREMENT_INDOOR_BIKE; in.present = BIT(FTMS_M_SPEED); in.value[FTMS_M_SPEED] = 1;
  for (i = 0U; i < 4U; ++i) {
    ftms_measurement_format_options bad = {FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE, FTMS_TREADMILL_PACE_UINT16};
    if (i < 2U) bad.resistance_format = (ftms_measurement_resistance_format)(i ? 256 : -1);
    else bad.treadmill_pace_format = (ftms_treadmill_pace_format)(i == 3U ? 256 : -1);
    memset(packets, 0xa5, sizeof packets); memcpy(saved, packets, sizeof packets); count = old = 99U;
    assert(ftms_measurement_plan_with_format(&in, &bad, 4U, packets, 2U, &count) == FTMS_ERROR_KIND);
    assert(count == old && memcmp(packets, saved, sizeof packets) == 0);
    assert(ftms_measurement_plan_with_format(&in, &bad, 4U, NULL, 0U, &count) == FTMS_ERROR_KIND && count == old);
  }
  memset(packets, 0xa5, sizeof packets); memcpy(saved, packets, sizeof packets); count = old = 99U;
  assert(ftms_measurement_plan_with_format(&in, &signed_resistance, 3U, packets, 2U, &count) == FTMS_ERROR_LENGTH);
  assert(count == old && memcmp(packets, saved, sizeof packets) == 0);
  assert(ftms_measurement_plan_with_format(&in, &signed_resistance, 4U, packets, 0U, &count) == FTMS_ERROR_LENGTH);
  assert(count == old && memcmp(packets, saved, sizeof packets) == 0);
  in.flags = 1U;
  assert(ftms_measurement_plan_with_format(&in, &signed_resistance, 4U, packets, 2U, &count) == FTMS_ERROR_RANGE);
  assert(count == old && memcmp(packets, saved, sizeof packets) == 0);
}

static void planner(void) {
  const ftms_measurement_kind kinds[] = {
    FTMS_MEASUREMENT_TREADMILL, FTMS_MEASUREMENT_CROSS_TRAINER,
    FTMS_MEASUREMENT_STEP_CLIMBER, FTMS_MEASUREMENT_STAIR_CLIMBER,
    FTMS_MEASUREMENT_ROWER, FTMS_MEASUREMENT_INDOOR_BIKE };
  const uint32_t flags[] = {8190U, 65534U, 510U, 1022U, 8190U, 8190U};
  const uint64_t fields[] = {UINT64_C(0x3ffff), UINT64_C(0x7efe7f), UINT64_C(0x18cfe20),
                             UINT64_C(0x9cfe20), UINT64_C(0xe62ff84), UINT64_C(0x3062fe07)};
  size_t k;
  for (k = 0U; k < sizeof kinds / sizeof *kinds; ++k) {
    ftms_measurement in, decoded; ftms_measurement_packet packets[FTMS_MEASUREMENT_PLAN_MAX_PACKETS];
    size_t count = 99U, i; uint64_t present = 0U, unavailable = 0U;
    memset(&in, 0, sizeof in); in.kind = kinds[k]; in.flags = flags[k]; in.present = fields[k];
    for (i = 0U; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i) in.value[i] = (int32_t)(i + 1U);
    if (k == 1U) { in.flags |= UINT32_C(0x8000); in.backward = 1U; }
    assert(ftms_measurement_plan(&in, 20U, NULL, 0U, &count) == FTMS_OK);
    assert(count > 1U && count < FTMS_MEASUREMENT_PLAN_MAX_PACKETS);
    assert(ftms_measurement_plan(&in, 20U, packets, count, &count) == FTMS_OK);
    for (i = 0U; i < count; ++i) {
      assert(packets[i].length <= 20U);
      assert(ftms_decode_measurement(in.kind, packets[i].value, packets[i].length, &decoded) == FTMS_OK);
      assert(decoded.truncated == 0U && decoded.reserved_flags == 0U);
      assert(decoded.more_data == (uint8_t)(i + 1U < count));
      assert(decoded.backward == (uint8_t)(k == 1U));
      present |= decoded.present; unavailable |= decoded.unavailable;
      for (size_t f = 0U; f < FTMS_MEASUREMENT_FIELD_COUNT; ++f)
        if ((decoded.present & BIT(f)) != 0U) assert(decoded.value[f] == in.value[f]);
    }
    assert(present == in.present && unavailable == in.unavailable);
    { ftms_measurement_packet old_packets[FTMS_MEASUREMENT_PLAN_MAX_PACKETS], null_packets[FTMS_MEASUREMENT_PLAN_MAX_PACKETS];
      size_t old_count, null_count;
      assert(ftms_measurement_plan(&in, 20U, old_packets, FTMS_MEASUREMENT_PLAN_MAX_PACKETS, &old_count) == FTMS_OK);
      assert(ftms_measurement_plan_with_format(&in, NULL, 20U, null_packets, FTMS_MEASUREMENT_PLAN_MAX_PACKETS, &null_count) == FTMS_OK);
      assert(old_count == null_count);
      for (i = 0U; i < old_count; ++i) assert(old_packets[i].length == null_packets[i].length &&
        memcmp(old_packets[i].value, null_packets[i].value, old_packets[i].length) == 0);
    }
  }
  { /* A minimal record is one final notification, and too-small budgets are atomic. */
    ftms_measurement in; ftms_measurement_packet packets[2], saved[2]; size_t count = 7U, old = count;
    memset(&in, 0, sizeof in); in.kind = FTMS_MEASUREMENT_INDOOR_BIKE;
    in.present = BIT(FTMS_M_SPEED); in.value[FTMS_M_SPEED] = 1;
    memset(packets, 0xa5, sizeof packets); memcpy(saved, packets, sizeof packets);
    assert(ftms_measurement_plan(&in, 4U, packets, 2U, &count) == FTMS_OK && count == 1U);
    memcpy(saved, packets, sizeof packets); count = old;
    assert(ftms_measurement_plan(&in, 3U, packets, 2U, &count) == FTMS_ERROR_LENGTH);
    assert(count == old && memcmp(packets, saved, sizeof packets) == 0);
    memcpy(saved, packets, sizeof packets);
    assert(ftms_measurement_plan(&in, 4U, packets, 0U, &count) == FTMS_ERROR_LENGTH);
    assert(memcmp(packets, saved, sizeof packets) == 0);
    assert(ftms_measurement_plan(&in, 3U, NULL, 0U, &count) == FTMS_ERROR_LENGTH);
    in.flags = 1U;
    assert(ftms_measurement_plan(&in, 20U, NULL, 0U, &count) == FTMS_ERROR_RANGE);
  }
  { /* Literal independent wire expectation: never concatenate/slice flags. */
    ftms_measurement in; ftms_measurement_packet packets[2]; size_t count;
    const uint8_t first[] = {0x03U, 0x00U, 0x2eU, 0x16U};
    const uint8_t last[] = {0x00U, 0x00U, 0xd2U, 0x04U};
    memset(&in, 0, sizeof in); in.kind = FTMS_MEASUREMENT_INDOOR_BIKE; in.flags = 2U;
    in.present = BIT(FTMS_M_SPEED) | BIT(FTMS_M_AVERAGE_SPEED);
    in.value[FTMS_M_SPEED] = 1234; in.value[FTMS_M_AVERAGE_SPEED] = 5678;
    assert(ftms_measurement_plan(&in, 4U, packets, 2U, &count) == FTMS_OK && count == 2U);
    assert(packets[0].length == sizeof first && memcmp(packets[0].value, first, sizeof first) == 0);
    assert(packets[1].length == sizeof last && memcmp(packets[1].value, last, sizeof last) == 0);
    assert(ftms_measurement_plan(&in, 64U, packets, 2U, &count) == FTMS_OK && count == 1U);
  }
  formatted_planner_regressions();
}

static void record_assembly(void) {
  const ftms_measurement_kind kinds[] = {
    FTMS_MEASUREMENT_TREADMILL, FTMS_MEASUREMENT_CROSS_TRAINER,
    FTMS_MEASUREMENT_STEP_CLIMBER, FTMS_MEASUREMENT_STAIR_CLIMBER,
    FTMS_MEASUREMENT_ROWER, FTMS_MEASUREMENT_INDOOR_BIKE };
  const uint32_t flags[] = {8190U, 65534U, 510U, 1022U, 8190U, 8190U};
  const uint64_t fields[] = {UINT64_C(0x3ffff), UINT64_C(0x7efe7f), UINT64_C(0x18cfe20),
                             UINT64_C(0x9cfe20), UINT64_C(0xe62ff84), UINT64_C(0x3062fe07)};
  size_t k;
  for (k = 0U; k < sizeof kinds / sizeof *kinds; ++k) {
    ftms_measurement source, out, formatted_out, pending, formatted_pending;
    ftms_measurement_packet packets[32];
    ftms_record_context context;
    ftms_record_format_context formatted_context;
    size_t count, i;
    memset(&source, 0, sizeof source); source.kind = kinds[k]; source.flags = flags[k];
    source.present = fields[k];
    for (i = 0U; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i) source.value[i] = (int32_t)(i + 10U);
    if (k == 0U) {
      source.unavailable = BIT(FTMS_M_INCLINATION);
      source.value[FTMS_M_INCLINATION] = 0;
    }
    if (k == 1U) source.flags |= UINT32_C(0x8000);
    assert(ftms_measurement_plan(&source, 20U, packets, 32U, &count) == FTMS_OK && count > 1U);
    memset(&out, 0xa5, sizeof out);
    memset(&formatted_out, 0xa5, sizeof formatted_out);
    pending = out;
    formatted_pending = formatted_out;
    assert(ftms_record_init(&context, kinds[k], 7U, 10U) == FTMS_RECORD_PENDING);
    assert(ftms_record_init_with_format(&formatted_context, kinds[k], NULL, 7U, 10U) == FTMS_RECORD_PENDING);
    for (i = 0U; i < count; ++i) {
      ftms_record_status status = ftms_record_feed(&context, packets[i].value, packets[i].length,
                                                    7U, (uint32_t)i, &out);
      ftms_record_status formatted_status = ftms_record_feed_with_format(&formatted_context,
        packets[i].value, packets[i].length, 7U, (uint32_t)i, &formatted_out);
      assert(status == (i + 1U == count ? FTMS_RECORD_COMPLETE : FTMS_RECORD_PENDING));
      assert(formatted_status == status);
      if (status == FTMS_RECORD_PENDING) {
        same_measurement(&out, &pending);
        same_measurement(&formatted_out, &formatted_pending);
      }
    }
    same_measurement(&out, &formatted_out);
    assert(out.flags == source.flags && out.present == source.present &&
           out.unavailable == source.unavailable && out.more_data == 0U);
    for (i = 0U; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i)
      if ((out.present & BIT(i)) != 0U) assert(out.value[i] == source.value[i]);
  }
  { /* Literal wire fragments: pending, final mandatory group, and standalone. */
    uint8_t optional[] = {0x03U, 0x00U, 0x2eU, 0x16U};
    uint8_t final[] = {0x00U, 0x00U, 0xd2U, 0x04U};
    ftms_record_context context; ftms_measurement out, saved;
    memset(&out, 0x5a, sizeof out); saved = out;
    assert(ftms_record_init(&context, FTMS_MEASUREMENT_INDOOR_BIKE, 1U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, optional, sizeof optional, 1U, 100U, &out) == FTMS_RECORD_PENDING);
    assert(memcmp(&out, &saved, sizeof out) == 0);
    assert(ftms_record_feed(&context, final, sizeof final, 1U, 104U, &out) == FTMS_RECORD_COMPLETE);
    assert(out.bytes_read == 0U);
    assert(out.flags == 2U && out.present == (BIT(FTMS_M_SPEED)|BIT(FTMS_M_AVERAGE_SPEED)) &&
           out.value[FTMS_M_SPEED] == 1234 && out.value[FTMS_M_AVERAGE_SPEED] == 5678);
    assert(ftms_record_feed(&context, final, sizeof final, 1U, 105U, &out) == FTMS_RECORD_COMPLETE);
    assert(out.bytes_read == sizeof final);
    assert(ftms_record_feed(&context, optional, sizeof optional, 1U, 200U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, final, sizeof final, 2U, 205U, &out) == FTMS_RECORD_GENERATION);
    assert(context.active == 0U);
  }
  { /* Invalid/rejected input clears pending state and never changes output. */
    uint8_t optional[] = {0x03U, 0x00U, 0x2eU, 0x16U};
    uint8_t duplicate[] = {0x03U, 0x00U, 0x2eU, 0x16U};
    uint8_t final[] = {0x00U, 0x00U, 0xd2U, 0x04U};
    uint8_t malformed[] = {0x01U, 0x20U};
    ftms_record_context context; ftms_measurement out, saved;
    memset(&out, 0x33, sizeof out); saved = out;
    assert(ftms_record_init(&context, FTMS_MEASUREMENT_INDOOR_BIKE, 1U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, optional, sizeof optional, 1U, 1U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, duplicate, sizeof duplicate, 1U, 2U, &out) == FTMS_RECORD_INVALID);
    assert(memcmp(&out, &saved, sizeof out) == 0 && context.active == 0U);
    assert(ftms_record_feed(&context, malformed, sizeof malformed, 1U, 3U, &out) == FTMS_RECORD_INVALID);
    assert(ftms_record_feed(&context, optional, sizeof optional, 1U, UINT32_MAX - 2U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, final, sizeof final, 1U, 2U, &out) == FTMS_RECORD_EXPIRED);
    assert(memcmp(&out, &saved, sizeof out) == 0);
    assert(ftms_record_feed(&context, optional, sizeof optional, 2U, 3U, &out) == FTMS_RECORD_GENERATION);
    assert(ftms_record_init(&context, FTMS_MEASUREMENT_INDOOR_BIKE, 1U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, optional, sizeof optional, 1U, 1U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, final, sizeof final, 1U, 6U, &out) == FTMS_RECORD_EXPIRED);
    assert(ftms_record_init(NULL, FTMS_MEASUREMENT_INDOOR_BIKE, 1U, 5U) == FTMS_RECORD_INVALID);
    assert(ftms_record_init(&context, (ftms_measurement_kind)6, 1U, 5U) == FTMS_RECORD_INVALID);
    assert(ftms_record_init(&context, FTMS_MEASUREMENT_INDOOR_BIKE, 1U, 0U) == FTMS_RECORD_INVALID);
    assert(ftms_record_feed(NULL, final, sizeof final, 1U, 1U, &out) == FTMS_RECORD_INVALID);
  }
  { /* Cross Trainer direction is record-scoped and cannot change mid-record. */
    uint8_t optional[] = {0x03U, 0x00U, 0x00U, 0x01U, 0x00U};
    uint8_t final_backward[] = {0x00U, 0x80U, 0x00U, 0x02U, 0x00U};
    ftms_record_context context; ftms_measurement out, saved;
    memset(&out, 0x11, sizeof out); saved = out;
    assert(ftms_record_init(&context, FTMS_MEASUREMENT_CROSS_TRAINER, 1U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, optional, sizeof optional, 1U, 1U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&context, final_backward, sizeof final_backward, 1U, 2U, &out) == FTMS_RECORD_INVALID);
    assert(context.active == 0U && memcmp(&out, &saved, sizeof out) == 0);
  }
}

static void same_measurement(const ftms_measurement *left, const ftms_measurement *right) {
  size_t i;
  assert(left->kind == right->kind && left->flags == right->flags &&
         left->present == right->present && left->unavailable == right->unavailable &&
         left->more_data == right->more_data && left->backward == right->backward &&
         left->truncated == right->truncated && left->trailing_bytes == right->trailing_bytes &&
         left->reserved_flags == right->reserved_flags && left->bytes_read == right->bytes_read);
  for (i = 0U; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i)
    assert(left->value[i] == right->value[i]);
}

static void default_format_context_equivalence(void) {
  static const uint8_t treadmill[] = {0,0,1,0};
  static const uint8_t cross[] = {0,0,0,1,0};
  static const uint8_t step[] = {0,0,1,0,2,0};
  static const uint8_t stair[] = {0,0,1,0};
  static const uint8_t rower[] = {0,0,1,2,0};
  static const uint8_t bike[] = {0,0,1,0};
  const struct case_def { ftms_measurement_kind kind; const uint8_t *data; size_t size; } cases[] = {
    {FTMS_MEASUREMENT_TREADMILL,treadmill,sizeof treadmill},
    {FTMS_MEASUREMENT_CROSS_TRAINER,cross,sizeof cross},
    {FTMS_MEASUREMENT_STEP_CLIMBER,step,sizeof step},
    {FTMS_MEASUREMENT_STAIR_CLIMBER,stair,sizeof stair},
    {FTMS_MEASUREMENT_ROWER,rower,sizeof rower},
    {FTMS_MEASUREMENT_INDOOR_BIKE,bike,sizeof bike} };
  size_t i;
  for (i = 0U; i < sizeof cases / sizeof *cases; ++i) {
    ftms_record_context old_context;
    ftms_record_format_context new_context;
    ftms_measurement old_out = {0}, new_out = {0};
    assert(ftms_record_init(&old_context, cases[i].kind, 9U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_init_with_format(&new_context, cases[i].kind, NULL, 9U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&old_context, cases[i].data, cases[i].size, 9U, 1U, &old_out) == FTMS_RECORD_COMPLETE);
    assert(ftms_record_feed_with_format(&new_context, cases[i].data, cases[i].size, 9U, 1U, &new_out) == FTMS_RECORD_COMPLETE);
    same_measurement(&old_out, &new_out);
  }
}

static void formatted_record_assembly(void) {
  const ftms_measurement_format_options signed_resistance = {
    FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS, FTMS_TREADMILL_PACE_UINT16};
  const ftms_measurement_format_options legacy_pace = {
    FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE, FTMS_TREADMILL_PACE_UINT8_LEGACY};
  const uint8_t bike_first[] = {0x61,0x00,0x78,0x00,0x2c,0x01};
  const uint8_t bike_second[] = {0x01,0x08,0x85,0x03};
  const uint8_t bike_final[] = {0x00,0x00,0x01,0x00};
  const uint8_t bike_complete[] = {0x60,0x08,0x01,0x00,0x78,0x00,0x2c,0x01,0x85,0x03};
  const uint8_t tread_first[] = {0x61,0x00,0x2a,0x2b};
  const uint8_t tread_second[] = {0x01,0x04,0x85,0x03};
  const uint8_t tread_final[] = {0x00,0x00,0xe8,0x03};
  const uint8_t tread_complete[] = {0x60,0x04,0xe8,0x03,0x2a,0x2b,0x85,0x03};
  ftms_record_format_context context, other;
  ftms_measurement out, saved, decoded;
  uint8_t encoded[64]; size_t written;

  memset(&context, 0xa5, sizeof context);
  { ftms_record_format_context before = context;
    ftms_measurement_format_options bad = {(ftms_measurement_resistance_format)-1,
      FTMS_TREADMILL_PACE_UINT16};
    assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, &bad, 1U, 5U) == FTMS_RECORD_INVALID);
    assert(memcmp(&context, &before, sizeof context) == 0);
    bad.resistance_format = FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE;
    bad.treadmill_pace_format = (ftms_treadmill_pace_format)256;
    assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, &bad, 1U, 5U) == FTMS_RECORD_INVALID);
    assert(memcmp(&context, &before, sizeof context) == 0); }
  assert(ftms_record_init_with_format(NULL, FTMS_MEASUREMENT_INDOOR_BIKE, &signed_resistance, 1U, 5U) == FTMS_RECORD_INVALID);
  /* Copy before writing permits a source-options pointer into the destination. */
  context.options = signed_resistance;
  assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, &context.options, 1U, 5U) == FTMS_RECORD_PENDING);
  assert(context.options.resistance_format == FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS);
  { ftms_measurement_format_options mutable_options = signed_resistance;
    assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, &mutable_options, 1U, 5U) == FTMS_RECORD_PENDING);
    mutable_options.resistance_format = FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE; }
  /* The context owns a copy, not the caller's option object. */
  assert(ftms_record_init_with_format(&other, FTMS_MEASUREMENT_INDOOR_BIKE, NULL, 1U, 5U) == FTMS_RECORD_PENDING);
  memset(&out, 0x5a, sizeof out); saved = out;
  assert(ftms_record_feed_with_format(&context, bike_first, sizeof bike_first, 1U, 1U, &out) == FTMS_RECORD_PENDING);
  assert(memcmp(&out, &saved, sizeof out) == 0);
  assert(ftms_record_feed_with_format(&other, bike_first, sizeof bike_first, 1U, 1U, &out) == FTMS_RECORD_INVALID);
  assert(ftms_record_feed_with_format(&context, bike_second, sizeof bike_second, 1U, 2U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, bike_final, sizeof bike_final, 1U, 3U, &out) == FTMS_RECORD_COMPLETE);
  assert(out.flags == 0x860U && out.present == (BIT(FTMS_M_SPEED)|BIT(FTMS_M_RESISTANCE)|BIT(FTMS_M_POWER)|BIT(FTMS_M_ELAPSED_TIME)) &&
         out.value[FTMS_M_SPEED] == 1 && out.value[FTMS_M_RESISTANCE] == 120 &&
         out.value[FTMS_M_POWER] == 300 && out.value[FTMS_M_ELAPSED_TIME] == 901 && out.bytes_read == 0U);
  assert(ftms_encode_measurement_with_format(&out, &signed_resistance, encoded, sizeof encoded, &written) == FTMS_OK);
  assert(written == sizeof bike_complete && memcmp(encoded, bike_complete, sizeof bike_complete) == 0);
  assert(ftms_decode_measurement_with_format(FTMS_MEASUREMENT_INDOOR_BIKE, encoded, written, &signed_resistance, &decoded) == FTMS_OK);
  assert(decoded.value[FTMS_M_RESISTANCE] == 120);
  /* Default assembly rejects the alternate bytes; it never guesses a profile. */
  { ftms_record_context old;
    assert(ftms_record_init(&old, FTMS_MEASUREMENT_INDOOR_BIKE, 1U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed(&old, bike_first, sizeof bike_first, 1U, 1U, &decoded) == FTMS_RECORD_INVALID); }

  assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_TREADMILL, &legacy_pace, 2U, 5U) == FTMS_RECORD_PENDING);
  assert(ftms_record_init_with_format(&other, FTMS_MEASUREMENT_INDOOR_BIKE, &signed_resistance, 2U, 5U) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, tread_first, sizeof tread_first, 2U, 1U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&other, bike_first, sizeof bike_first, 2U, 1U, &out) == FTMS_RECORD_PENDING);
  ftms_record_reset_with_format(&context);
  assert(ftms_record_feed_with_format(&context, tread_final, sizeof tread_final, 2U, 2U, &out) == FTMS_RECORD_COMPLETE);
  assert(out.value[FTMS_M_SPEED] == 1000 && out.bytes_read == sizeof tread_final);
  assert(ftms_record_feed_with_format(&other, bike_second, sizeof bike_second, 2U, 2U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&other, bike_final, sizeof bike_final, 2U, 3U, &out) == FTMS_RECORD_COMPLETE);
  assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_TREADMILL, &legacy_pace, 2U, 5U) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, tread_first, sizeof tread_first, 2U, 1U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, tread_second, sizeof tread_second, 2U, 2U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, tread_final, sizeof tread_final, 2U, 3U, &out) == FTMS_RECORD_COMPLETE);
  assert(out.flags == 0x460U && out.value[FTMS_M_SPEED] == 1000 && out.value[FTMS_M_INSTANTANEOUS_PACE] == 42 &&
         out.value[FTMS_M_AVERAGE_PACE] == 43 && out.value[FTMS_M_ELAPSED_TIME] == 901);
  assert(ftms_encode_measurement_with_format(&out, &legacy_pace, encoded, sizeof encoded, &written) == FTMS_OK &&
         written == sizeof tread_complete && memcmp(encoded, tread_complete, sizeof tread_complete) == 0);

  /* Negative resistance is available in both remaining resistance families. */
  { const uint8_t cross_first[] = {0x81,0x00,0x00,0xf4,0xff};
    const uint8_t cross_final[] = {0x00,0x00,0x00,0x01,0x00};
    const uint8_t rower_first[] = {0x81,0x00,0xf4,0xff};
    const uint8_t rower_final[] = {0x00,0x00,0x02,0x03,0x00};
    assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_CROSS_TRAINER, &signed_resistance, 2U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed_with_format(&context, cross_first, sizeof cross_first, 2U, 1U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed_with_format(&context, cross_final, sizeof cross_final, 2U, 2U, &out) == FTMS_RECORD_COMPLETE);
    assert(out.value[FTMS_M_RESISTANCE] == -12 && out.unavailable == 0U && out.value[FTMS_M_SPEED] == 1);
    assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_ROWER, &signed_resistance, 2U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed_with_format(&context, rower_first, sizeof rower_first, 2U, 1U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed_with_format(&context, rower_final, sizeof rower_final, 2U, 2U, &out) == FTMS_RECORD_COMPLETE);
    assert(out.value[FTMS_M_RESISTANCE] == -12 && out.unavailable == 0U && out.value[FTMS_M_STROKE_COUNT] == 3);
  }

  /* Changing format by reinitialization must discard the old partial record. */
  assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, &signed_resistance, 2U, 5U) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, bike_first, sizeof bike_first, 2U, 1U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, NULL, 2U, 5U) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, bike_final, sizeof bike_final, 2U, 2U, &out) == FTMS_RECORD_COMPLETE);
  assert(out.present == BIT(FTMS_M_SPEED) && out.value[FTMS_M_RESISTANCE] == 0);

  /* Rejected variants clear pending state and leave output canaries intact. */
  memset(&out, 0x33, sizeof out); saved = out;
  assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, &signed_resistance, 3U, 5U) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, bike_first, sizeof bike_first, 3U, UINT32_MAX - 2U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, bike_first, sizeof bike_first, 3U, UINT32_MAX - 1U, &out) == FTMS_RECORD_INVALID);
  assert(context.record.active == 0U && memcmp(&out, &saved, sizeof out) == 0);
  assert(ftms_record_feed_with_format(&context, bike_first, sizeof bike_first, 3U, UINT32_MAX - 2U, &out) == FTMS_RECORD_PENDING);
  assert(ftms_record_feed_with_format(&context, bike_final, sizeof bike_final, 3U, 2U, &out) == FTMS_RECORD_EXPIRED);
  assert(memcmp(&out, &saved, sizeof out) == 0);
  assert(ftms_record_feed_with_format(&context, bike_first, sizeof bike_first - 1U, 3U, 3U, &out) == FTMS_RECORD_INVALID);
  { uint8_t trailing[sizeof bike_first + 1U];
    memcpy(trailing, bike_first, sizeof bike_first); trailing[sizeof bike_first] = 0U;
    assert(ftms_record_feed_with_format(&context, trailing, sizeof trailing, 3U, 3U, &out) == FTMS_RECORD_INVALID); }
  assert(ftms_record_feed_with_format(&context, bike_first, sizeof bike_first, 4U, 3U, &out) == FTMS_RECORD_GENERATION);
  assert(memcmp(&out, &saved, sizeof out) == 0);
  { const uint8_t malformed[] = {0x01,0x20};
    const uint8_t cross_optional[] = {0x03,0x00,0x00,0x01,0x00};
    const uint8_t cross_backward[] = {0x00,0x80,0x00,0x02,0x00};
    assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_INDOOR_BIKE, &signed_resistance, 3U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed_with_format(&context, malformed, sizeof malformed, 3U, 3U, &out) == FTMS_RECORD_INVALID);
    assert(memcmp(&out, &saved, sizeof out) == 0);
    assert(ftms_record_init_with_format(&context, FTMS_MEASUREMENT_CROSS_TRAINER, &signed_resistance, 3U, 5U) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed_with_format(&context, cross_optional, sizeof cross_optional, 3U, 3U, &out) == FTMS_RECORD_PENDING);
    assert(ftms_record_feed_with_format(&context, cross_backward, sizeof cross_backward, 3U, 4U, &out) == FTMS_RECORD_INVALID);
    assert(context.record.active == 0U && memcmp(&out, &saved, sizeof out) == 0); }
}

int main(void) {
  one(FTMS_MEASUREMENT_CROSS_TRAINER, 0x101U, FTMS_M_POWER, 32767);
  one(FTMS_MEASUREMENT_ROWER, 0x21U, FTMS_M_POWER, 32767);
  one(FTMS_MEASUREMENT_INDOOR_BIKE, 0x41U, FTMS_M_POWER, 32767);
  one(FTMS_MEASUREMENT_CROSS_TRAINER, 0x201U, FTMS_M_AVERAGE_POWER, 32767);
  one(FTMS_MEASUREMENT_ROWER, 0x41U, FTMS_M_AVERAGE_POWER, 32767);
  one(FTMS_MEASUREMENT_INDOOR_BIKE, 0x81U, FTMS_M_AVERAGE_POWER, 32767);
  one(FTMS_MEASUREMENT_TREADMILL, 3U, FTMS_M_AVERAGE_SPEED, 65535);
  one(FTMS_MEASUREMENT_INDOOR_BIKE, 0x201U, FTMS_M_HEART_RATE, 255);
  one(FTMS_MEASUREMENT_TREADMILL, 3U, FTMS_M_AVERAGE_SPEED, 1234);
  one(FTMS_MEASUREMENT_CROSS_TRAINER, 3U, FTMS_M_AVERAGE_SPEED, 1234);
  one(FTMS_MEASUREMENT_STEP_CLIMBER, 3U, FTMS_M_STEP_RATE, 40);
  one(FTMS_MEASUREMENT_STAIR_CLIMBER, 3U, FTMS_M_STEP_RATE, 40);
  one(FTMS_MEASUREMENT_ROWER, 3U, FTMS_M_AVERAGE_STROKE_RATE, 40);
  one(FTMS_MEASUREMENT_INDOOR_BIKE, 3U, FTMS_M_AVERAGE_SPEED, 1234);
  full_payload_prefixes(FTMS_MEASUREMENT_TREADMILL, 8190U, UINT64_C(0x3ffff), 36U);
  full_payload_prefixes(FTMS_MEASUREMENT_CROSS_TRAINER, 65534U, UINT64_C(0x7efe7f), 40U);
  full_payload_prefixes(FTMS_MEASUREMENT_STEP_CLIMBER, 510U, UINT64_C(0x18cfe20), 23U);
  full_payload_prefixes(FTMS_MEASUREMENT_STAIR_CLIMBER, 1022U, UINT64_C(0x9cfe20), 23U);
  full_payload_prefixes(FTMS_MEASUREMENT_ROWER, 8190U, UINT64_C(0xe62ff84), 29U);
  full_payload_prefixes(FTMS_MEASUREMENT_INDOOR_BIKE, 8190U, UINT64_C(0x3062fe07), 29U);
  invalid_inputs(); sentinels_and_overlap(); format_overrides(); planner(); record_assembly();
  default_format_context_equivalence(); formatted_record_assembly();
  return 0;
}
