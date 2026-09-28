#include <stdio.h>
#include <string.h>
#include "ftms/capabilities.h"
#include "ftms/capabilities.h" /* Self-contained and double-includable. */

#define CHECK(x) do { if (!(x)) { \
  fprintf(stderr, "cap CHECK %d: %s\n", __LINE__, #x); return 1; \
} } while (0)

typedef struct fixture {
  ftms_cap_characteristic chars[16];
  uint8_t feature[8];
  ftms_cap_snapshot snapshot;
  ftms_cap_output out;
  ftms_cap_observation observations[16];
  ftms_cap_diagnostic diagnostics[64];
} fixture;

static void uuid(uint8_t out[16], unsigned value) {
  static const uint8_t tail[12] = {0,0,0x10,0,0x80,0,0,0x80,0x5f,0x9b,0x34,0xfb};
  out[0] = 0; out[1] = 0;
  out[2] = (uint8_t)(value >> 8); out[3] = (uint8_t)value;
  memcpy(out + 4, tail, sizeof tail);
}

static void setup(fixture *f) {
  static const uint8_t speed[] = {100,0,0xb8,0x0b,50,0};
  static const uint8_t inclination[] = {0x9c,0xff,150,0,5,0};
  static const uint8_t resistance[] = {0,100,1};
  static const uint8_t heart_rate[] = {60,200,1};
  static const uint8_t power[] = {0x9c,0xff,0xdc,5,5,0};
  const uint8_t *ranges[5] = {speed, inclination, resistance, heart_rate, power};
  const size_t sizes[5] = {6,6,3,3,6};
  size_t i;
  memset(f, 0, sizeof *f);
  f->feature[4] = 0xff; f->feature[5] = 0xff; f->feature[6] = 1;
  uuid(f->chars[0].uuid, 0x2acc);
  f->chars[0].properties = FTMS_CAP_PROP_READ;
  f->chars[0].read_state = FTMS_CAP_READ_SUCCESS;
  f->chars[0].read_bytes = f->feature; f->chars[0].read_size = 8;
  uuid(f->chars[1].uuid, 0x2ad9);
  f->chars[1].properties = FTMS_CAP_PROP_WRITE | FTMS_CAP_PROP_INDICATE;
  uuid(f->chars[2].uuid, 0x2ada); f->chars[2].properties = FTMS_CAP_PROP_NOTIFY;
  for (i = 0; i < 5U; ++i) {
    uuid(f->chars[i + 3U].uuid, 0x2ad4U + (unsigned)i);
    f->chars[i + 3U].properties = FTMS_CAP_PROP_READ;
    f->chars[i + 3U].read_state = FTMS_CAP_READ_SUCCESS;
    f->chars[i + 3U].read_bytes = ranges[i]; f->chars[i + 3U].read_size = sizes[i];
  }
  f->snapshot.discovery = FTMS_CAP_DISCOVERY_COMPLETE;
  f->snapshot.service_scope = FTMS_CAP_SERVICE_PRESENT;
  f->snapshot.generation = 7;
  f->snapshot.characteristics = f->chars; f->snapshot.characteristic_count = 8;
  f->out.observations = f->observations; f->out.observation_capacity = 16;
  f->out.diagnostics = f->diagnostics; f->out.diagnostic_capacity = 64;
}

static int evaluate(fixture *f) {
  ftms_cap_requirements q;
  CHECK(ftms_capability_requirements(&f->snapshot, &q) == FTMS_OK);
  CHECK(ftms_evaluate_capabilities(&f->snapshot, &f->out) == FTMS_OK);
  CHECK(q.observation_count == f->snapshot.characteristic_count);
  CHECK(q.observation_count == f->out.report.observation_count);
  CHECK(q.diagnostic_count == f->out.report.diagnostic_count);
  return 0;
}

static int test_target_mapping(void) {
  static const uint8_t opcodes[17] = {2,3,4,5,6,9,10,11,12,13,14,15,16,17,18,19,20};
  static const uint8_t range_indices[5] = {0,1,2,4,3};
  fixture f;
  unsigned bit, other;
  size_t op;
  for (bit = 0; bit < 17U; ++bit) {
    uint32_t mask = UINT32_C(1) << bit;
    setup(&f);
    f.feature[4] = (uint8_t)mask; f.feature[5] = (uint8_t)(mask >> 8);
    f.feature[6] = (uint8_t)(mask >> 16);
    /* No ranges at all for the remaining twelve targets. */
    if (bit >= 5U) f.snapshot.characteristic_count = 3;
    CHECK(evaluate(&f) == 0);
    CHECK(f.out.report.diagnostic_count == 0);
    CHECK(f.out.report.feature.target_raw == mask);
    for (op = 0; op < FTMS_CAP_OPERATION_COUNT; ++op) {
      const ftms_cap_operation *o = &f.out.report.operations[op];
      CHECK(o->opcode == op);
      CHECK(o->optional_in_table == (op == 18U || op == 19U));
      CHECK(o->reasons == 0);
      if (op == 0U || op == 1U || op == 7U || op == 8U) {
        CHECK(o->target_bit == FTMS_CAP_NO_TARGET);
        CHECK(o->declaration == FTMS_CAP_DECLARATION_SUPPORTED);
        CHECK(o->prerequisite == FTMS_CAP_PREREQUISITE_SATISFIED);
      }
    }
    for (other = 0; other < 17U; ++other) {
      const ftms_cap_operation *o = &f.out.report.operations[opcodes[other]];
      CHECK(o->target_bit == other);
      CHECK(o->declaration == (bit == other ? FTMS_CAP_DECLARATION_SUPPORTED : FTMS_CAP_DECLARATION_NOT_SUPPORTED));
      CHECK(o->prerequisite == (bit == other ? FTMS_CAP_PREREQUISITE_SATISFIED : FTMS_CAP_PREREQUISITE_NOT_APPLICABLE));
    }
    if (bit < 5U) {
      size_t index = (size_t)range_indices[bit] + 3U;
      f.chars[index].uuid[0] = 1; /* Unrelated vendor UUID, not the required range. */
      CHECK(evaluate(&f) == 0);
      CHECK(f.out.report.operations[opcodes[bit]].reasons == FTMS_CAP_REASON_RANGE_INVALID);
      CHECK(f.out.report.operations[opcodes[bit]].prerequisite == FTMS_CAP_PREREQUISITE_INCONSISTENT);
      CHECK(f.out.report.diagnostic_count == 1);
      CHECK(f.diagnostics[0].code == FTMS_CAP_DIAG_REQUIRED_RANGE_MISSING);
      CHECK(f.diagnostics[0].known_kind == FTMS_CAP_KIND_SPEED_RANGE + range_indices[bit]);
      CHECK(f.diagnostics[0].input_index == FTMS_CAP_NO_INDEX);
    }
  }
  return 0;
}

static int test_feature_and_range_states(void) {
  fixture f;
  unsigned reason;
  size_t op, range;
  setup(&f);
  f.feature[0] = 0xff; f.feature[1] = 0xff; f.feature[2] = 0xff; f.feature[3] = 0xff;
  f.feature[7] = 0x80;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.feature.machine_raw == UINT32_MAX);
  CHECK(f.out.report.feature.machine_unknown == UINT32_C(0xfffe0000));
  CHECK(f.out.report.feature.target_unknown == UINT32_C(0x80000000));
  for (reason = 0; reason <= (unsigned)FTMS_CAP_READ_REASON_DISCONNECTED; ++reason) {
    setup(&f);
    f.chars[0].read_state = FTMS_CAP_READ_FAILED;
    f.chars[0].read_reason = (ftms_cap_read_reason)reason;
    f.chars[0].read_bytes = NULL; f.chars[0].read_size = 0;
    CHECK(evaluate(&f) == 0);
    CHECK(f.out.report.feature.decode == FTMS_CAP_DECODE_FAILED);
    CHECK(f.out.report.operations[0].prerequisite == FTMS_CAP_PREREQUISITE_SATISFIED);
    for (op = 0; op < FTMS_CAP_OPERATION_COUNT; ++op) {
      if (f.out.report.operations[op].target_bit == FTMS_CAP_NO_TARGET) continue;
      CHECK(f.out.report.operations[op].declaration == FTMS_CAP_DECLARATION_UNKNOWN);
      CHECK(f.out.report.operations[op].prerequisite == FTMS_CAP_PREREQUISITE_INCOMPLETE);
      CHECK(f.out.report.operations[op].reasons == FTMS_CAP_REASON_FEATURE_UNAVAILABLE);
    }
    CHECK(f.observations[0].read_reason == (ftms_cap_read_reason)reason);
    CHECK(f.diagnostics[0].code == (reason == 2U ? FTMS_CAP_DIAG_READ_SECURITY_REQUIRED : FTMS_CAP_DIAG_READ_FAILED));
  }
  setup(&f);
  f.chars[0].read_bytes = NULL; f.chars[0].read_size = 0;
  CHECK(evaluate(&f) == 0); /* NULL/zero SUCCESS is evidence, not an API error. */
  CHECK(f.out.report.feature.decode == FTMS_CAP_DECODE_MALFORMED);
  CHECK(f.out.report.operations[2].reasons == FTMS_CAP_REASON_FEATURE_INVALID);
  f.chars[0].read_state = FTMS_CAP_READ_NOT_ATTEMPTED;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.feature.decode == FTMS_CAP_DECODE_NOT_ATTEMPTED);
  CHECK(f.out.report.operations[2].reasons == FTMS_CAP_REASON_FEATURE_UNAVAILABLE);
  setup(&f);
  f.chars[0].uuid[0] = 1;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.feature.presence == FTMS_CAP_PRESENCE_ABSENT);
  CHECK(f.out.report.operations[0].prerequisite == FTMS_CAP_PREREQUISITE_INCONSISTENT);
  CHECK(f.out.report.operations[2].declaration == FTMS_CAP_DECLARATION_UNKNOWN);
  setup(&f);
  f.chars[8] = f.chars[0]; f.snapshot.characteristic_count = 9;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.feature.presence == FTMS_CAP_PRESENCE_AMBIGUOUS);
  CHECK(f.out.report.feature.decode == FTMS_CAP_DECODE_NOT_ATTEMPTED);
  CHECK(f.out.report.feature.input_index == FTMS_CAP_NO_INDEX);
  CHECK(f.out.report.operations[2].prerequisite == FTMS_CAP_PREREQUISITE_INCONSISTENT);
  for (range = 0; range < 5U; ++range) {
    static const uint8_t opcodes[5] = {2,3,4,6,5};
    size_t index = range + 3U;
    setup(&f);
    f.chars[index].read_state = FTMS_CAP_READ_FAILED;
    f.chars[index].read_reason = FTMS_CAP_READ_REASON_SECURITY_REQUIRED;
    f.chars[index].read_bytes = NULL; f.chars[index].read_size = 0;
    CHECK(evaluate(&f) == 0);
    CHECK(f.out.report.ranges[range].decode == FTMS_CAP_DECODE_FAILED);
    CHECK(f.out.report.operations[opcodes[range]].reasons == FTMS_CAP_REASON_RANGE_UNAVAILABLE);
    f.chars[index].read_state = FTMS_CAP_READ_SUCCESS;
    f.chars[index].read_reason = FTMS_CAP_READ_REASON_NONE;
    CHECK(evaluate(&f) == 0);
    CHECK(f.out.report.ranges[range].decode == FTMS_CAP_DECODE_MALFORMED);
    CHECK(f.out.report.operations[opcodes[range]].reasons == FTMS_CAP_REASON_RANGE_INVALID);
    /* A known false target retains invalid evidence but is not promoted. */
    memset(f.feature + 4, 0, 4);
    CHECK(evaluate(&f) == 0);
    CHECK(f.out.report.operations[opcodes[range]].declaration == FTMS_CAP_DECLARATION_NOT_SUPPORTED);
    CHECK(f.out.report.operations[opcodes[range]].prerequisite == FTMS_CAP_PREREQUISITE_NOT_APPLICABLE);
    CHECK(f.out.report.ranges[range].decode == FTMS_CAP_DECODE_MALFORMED);
  }
  return 0;
}

static int test_discovery_and_properties(void) {
  fixture f;
  size_t i;
  unsigned scope;
  setup(&f);
  for (i = 0; i < 6U; ++i) {
    uuid(f.chars[i + 8U].uuid, 0x2acdU + (unsigned)i);
    f.chars[i + 8U].properties = FTMS_CAP_PROP_NOTIFY;
  }
  f.snapshot.characteristic_count = 14;
  CHECK(evaluate(&f) == 0);
  for (i = FTMS_CAP_KIND_TREADMILL; i <= FTMS_CAP_KIND_INDOOR_BIKE; ++i) {
    CHECK(f.out.report.presence[i] == FTMS_CAP_PRESENCE_UNIQUE);
  }
  f.chars[8].properties = 0;
  CHECK(evaluate(&f) == 0);
  CHECK(f.diagnostics[0].known_kind == FTMS_CAP_KIND_TREADMILL);
  CHECK(f.out.report.operations[2].prerequisite == FTMS_CAP_PREREQUISITE_SATISFIED);
  setup(&f);
  f.snapshot.discovery = FTMS_CAP_DISCOVERY_PARTIAL;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.operations[2].declaration == FTMS_CAP_DECLARATION_SUPPORTED);
  CHECK(f.out.report.operations[2].prerequisite == FTMS_CAP_PREREQUISITE_INCOMPLETE);
  CHECK(f.out.report.presence[FTMS_CAP_KIND_ROWER] == FTMS_CAP_PRESENCE_UNKNOWN);
  f.chars[1].properties = FTMS_CAP_PROP_WRITE;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.operations[2].prerequisite == FTMS_CAP_PREREQUISITE_INCONSISTENT);
  CHECK(f.out.report.operations[2].reasons == (FTMS_CAP_REASON_DISCOVERY_INCOMPLETE | FTMS_CAP_REASON_CONTROL_POINT_INVALID));
  setup(&f);
  f.chars[0].properties = FTMS_CAP_PROP_READ | FTMS_CAP_PROP_NOTIFY;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.feature.target_raw == UINT32_C(0x1ffff));
  CHECK(f.out.report.operations[2].declaration == FTMS_CAP_DECLARATION_SUPPORTED);
  CHECK(f.out.report.operations[2].prerequisite == FTMS_CAP_PREREQUISITE_INCONSISTENT);
  CHECK(f.diagnostics[0].code == FTMS_CAP_DIAG_EXCLUDED_PROPERTY_PRESENT);
  for (scope = 0; scope <= 3U; ++scope) {
    if (scope == (unsigned)FTMS_CAP_SERVICE_PRESENT) continue;
    setup(&f);
    f.snapshot.service_scope = (ftms_cap_service_scope)scope;
    CHECK(evaluate(&f) == 0);
    CHECK(f.out.report.feature.decode == FTMS_CAP_DECODE_NOT_ATTEMPTED);
    CHECK(f.out.report.feature.input_index == FTMS_CAP_NO_INDEX);
    CHECK(f.out.report.presence[FTMS_CAP_KIND_FEATURE] == FTMS_CAP_PRESENCE_UNIQUE);
    CHECK(f.out.report.operations[2].declaration == FTMS_CAP_DECLARATION_UNKNOWN);
    CHECK(f.out.report.operations[2].prerequisite == (scope == 2U ? FTMS_CAP_PREREQUISITE_INCONSISTENT : FTMS_CAP_PREREQUISITE_INCOMPLETE));
  }
  f.snapshot.service_scope = FTMS_CAP_SERVICE_ABSENT; f.snapshot.characteristic_count = 0;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.operations[2].declaration == FTMS_CAP_DECLARATION_NOT_SUPPORTED);
  CHECK(f.out.report.operations[2].prerequisite == FTMS_CAP_PREREQUISITE_NOT_APPLICABLE);
  setup(&f);
  f.chars[8] = f.chars[1]; f.snapshot.characteristic_count = 9;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.operations[0].declaration == FTMS_CAP_DECLARATION_UNKNOWN);
  CHECK(f.out.report.operations[2].prerequisite == FTMS_CAP_PREREQUISITE_INCONSISTENT);
  f.chars[8] = f.chars[7];
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.ranges[4].presence == FTMS_CAP_PRESENCE_AMBIGUOUS);
  CHECK(f.out.report.ranges[4].decode == FTMS_CAP_DECODE_NOT_ATTEMPTED);
  CHECK(f.out.report.operations[5].prerequisite == FTMS_CAP_PREREQUISITE_INCONSISTENT);
  CHECK(f.out.report.operations[6].prerequisite == FTMS_CAP_PREREQUISITE_SATISFIED);
  /* No hidden cache; overwrite the complete prior report on a new snapshot. */
  f.snapshot.characteristic_count = 0; f.snapshot.generation = UINT32_MAX;
  CHECK(evaluate(&f) == 0);
  CHECK(f.out.report.generation == UINT32_MAX);
  CHECK(f.out.report.feature.target_raw == 0);
  CHECK(f.out.report.feature.presence == FTMS_CAP_PRESENCE_ABSENT);
  return 0;
}

static int error_untouched(fixture *f, ftms_result expected, int check_requirements) {
  ftms_cap_output saved;
  ftms_cap_observation observations[16];
  ftms_cap_diagnostic diagnostics[64];
  ftms_cap_requirements q, before;
  memcpy(&saved, &f->out, sizeof saved);
  memcpy(observations, f->observations, sizeof observations);
  memcpy(diagnostics, f->diagnostics, sizeof diagnostics);
  CHECK(ftms_evaluate_capabilities(&f->snapshot, &f->out) == expected);
  CHECK(memcmp(&f->out, &saved, sizeof saved) == 0);
  CHECK(memcmp(f->observations, observations, sizeof observations) == 0);
  CHECK(memcmp(f->diagnostics, diagnostics, sizeof diagnostics) == 0);
  if (check_requirements) {
    memset(&q, 0xa5, sizeof q); memcpy(&before, &q, sizeof before);
    CHECK(ftms_capability_requirements(&f->snapshot, &q) == expected);
    CHECK(memcmp(&q, &before, sizeof q) == 0);
  }
  return 0;
}

static int test_argument_and_buffer_contract(void) {
  fixture f;
  ftms_cap_requirements q;
  unsigned i;
  setup(&f);
  CHECK(ftms_evaluate_capabilities(NULL, &f.out) == FTMS_ERROR_NULL);
  CHECK(ftms_evaluate_capabilities(&f.snapshot, NULL) == FTMS_ERROR_NULL);
  CHECK(ftms_capability_requirements(NULL, &q) == FTMS_ERROR_NULL);
  CHECK(ftms_capability_requirements(&f.snapshot, NULL) == FTMS_ERROR_NULL);
  for (i = 0; i < 2U; ++i) {
    int invalid = i ? 99 : -1;
    setup(&f); f.snapshot.discovery = (ftms_cap_discovery)invalid;
    CHECK(error_untouched(&f, FTMS_ERROR_KIND, 1) == 0);
    setup(&f); f.snapshot.service_scope = (ftms_cap_service_scope)invalid;
    CHECK(error_untouched(&f, FTMS_ERROR_KIND, 1) == 0);
    setup(&f); f.chars[0].read_state = (ftms_cap_read_state)invalid;
    CHECK(error_untouched(&f, FTMS_ERROR_KIND, 1) == 0);
    setup(&f); f.chars[0].read_reason = (ftms_cap_read_reason)invalid;
    CHECK(error_untouched(&f, FTMS_ERROR_KIND, 1) == 0);
  }
  setup(&f); f.snapshot.characteristic_count = SIZE_MAX;
  CHECK(error_untouched(&f, FTMS_ERROR_LENGTH, 1) == 0);
  setup(&f); f.snapshot.characteristics = NULL;
  CHECK(error_untouched(&f, FTMS_ERROR_NULL, 1) == 0);
  setup(&f); f.chars[0].read_bytes = NULL;
  CHECK(error_untouched(&f, FTMS_ERROR_NULL, 1) == 0);
  setup(&f); f.chars[0].read_state = FTMS_CAP_READ_FAILED;
  CHECK(error_untouched(&f, FTMS_ERROR_KIND, 1) == 0);
  setup(&f); f.chars[0].read_reason = FTMS_CAP_READ_REASON_GENERIC;
  CHECK(error_untouched(&f, FTMS_ERROR_KIND, 1) == 0);
  setup(&f); f.out.observation_capacity = 7;
  CHECK(error_untouched(&f, FTMS_ERROR_LENGTH, 0) == 0);
  setup(&f); f.out.observations = NULL;
  CHECK(error_untouched(&f, FTMS_ERROR_NULL, 0) == 0);
  setup(&f); f.chars[0].properties = 0; f.out.diagnostic_capacity = 0;
  CHECK(error_untouched(&f, FTMS_ERROR_LENGTH, 0) == 0);
  f.out.diagnostic_capacity = 64; f.out.diagnostics = NULL;
  CHECK(error_untouched(&f, FTMS_ERROR_NULL, 0) == 0);
  /* Exact-sized buffers, with the remaining allocated slots acting as canaries. */
  setup(&f); f.chars[0].properties = 0;
  memset(f.observations, 0xa5, sizeof f.observations);
  memset(f.diagnostics, 0xa5, sizeof f.diagnostics);
  f.out.observation_capacity = 8; f.out.diagnostic_capacity = 1;
  CHECK(evaluate(&f) == 0);
  {
    ftms_cap_observation guard;
    ftms_cap_diagnostic diag_guard;
    memset(&guard, 0xa5, sizeof guard); memset(&diag_guard, 0xa5, sizeof diag_guard);
    CHECK(memcmp(&guard, &f.observations[8], sizeof guard) == 0);
    CHECK(memcmp(&diag_guard, &f.diagnostics[1], sizeof diag_guard) == 0);
  }
  /* Zero-needed buffers may be NULL even with nonzero capacities. */
  setup(&f); f.out.diagnostics = NULL;
  CHECK(evaluate(&f) == 0);
  setup(&f); f.snapshot.characteristic_count = 0; f.snapshot.characteristics = NULL;
  f.out.observations = NULL; f.out.observation_capacity = 0;
  CHECK(evaluate(&f) == 0);
  return 0;
}

int test_capabilities(void) {
  CHECK(test_target_mapping() == 0);
  CHECK(test_feature_and_range_states() == 0);
  CHECK(test_discovery_and_properties() == 0);
  CHECK(test_argument_and_buffer_contract() == 0);
  puts("capability unit suites: mappings, read evidence, discovery/properties, API atomicity passed");
  return 0;
}
