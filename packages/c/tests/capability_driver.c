/* Host-only text-to-JSON test bridge. No production JSON/heap dependency. */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ftms/capabilities.h"

#define MAX_CHARS 128U
#define MAX_BYTES 1024U

static int digit(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}
static int hex(const char *s, uint8_t *out, size_t cap, size_t *n) {
  size_t i, length = strlen(s);
  if ((length & 1U) != 0U || length / 2U > cap) return 0;
  for (i = 0; i < length / 2U; ++i) {
    int high = digit(s[i * 2U]), low = digit(s[i * 2U + 1U]);
    if (high < 0 || low < 0) return 0;
    out[i] = (uint8_t)((unsigned)high * 16U + (unsigned)low);
  }
  *n = length / 2U;
  return 1;
}
static void index_json(size_t index) {
  if (index == FTMS_CAP_NO_INDEX) printf("null");
  else printf("%zu", index);
}
static void uuid_json(const uint8_t uuid[FTMS_CAP_UUID_BYTES]) {
  size_t i;
  for (i = 0; i < FTMS_CAP_UUID_BYTES; ++i) printf("%02x", (unsigned)uuid[i]);
}
static void report_json(const ftms_cap_output *out) {
  size_t i;
  const ftms_cap_report *r = &out->report;
  printf("{\"generation\":%" PRIu32 ",\"discovery\":%d,\"scope\":%d,"
         "\"observationCount\":%zu,\"diagnosticCount\":%zu,\"presence\":[",
         r->generation, (int)r->discovery, (int)r->service_scope,
         r->observation_count, r->diagnostic_count);
  for (i = 0; i < FTMS_CAP_KIND_COUNT; ++i) printf("%s%d", i ? "," : "", (int)r->presence[i]);
  printf("],\"feature\":[%d,%d,", (int)r->feature.presence, (int)r->feature.decode);
  index_json(r->feature.input_index);
  printf(",%" PRIu32 ",%" PRIu32 ",%" PRIu32 ",%" PRIu32 "],\"ranges\":[",
         r->feature.machine_raw, r->feature.target_raw, r->feature.machine_unknown, r->feature.target_unknown);
  for (i = 0; i < FTMS_CAP_RANGE_COUNT; ++i) {
    const ftms_cap_range_evidence *e = &r->ranges[i];
    printf("%s[%d,%d,", i ? "," : "", (int)e->presence, (int)e->decode);
    index_json(e->input_index);
    if (e->decode == FTMS_CAP_DECODE_VALID) {
      printf(",[%d,%" PRId32 ",%" PRId32 ",%" PRId32 ",%u,%d]]",
             (int)e->value.kind, e->value.minimum, e->value.maximum, e->value.increment,
             (unsigned)e->value.scale_divisor, (int)e->value.unit);
    } else printf(",null]");
  }
  printf("],\"operations\":[");
  for (i = 0; i < FTMS_CAP_OPERATION_COUNT; ++i) {
    const ftms_cap_operation *o = &r->operations[i];
    printf("%s[%u,%u,%u,%d,%d,%" PRIu32 "]", i ? "," : "", (unsigned)o->opcode,
           (unsigned)o->target_bit, (unsigned)o->optional_in_table, (int)o->declaration,
           (int)o->prerequisite, o->reasons);
  }
  printf("],\"observations\":[");
  for (i = 0; i < r->observation_count; ++i) {
    const ftms_cap_observation *o = &out->observations[i];
    printf("%s[%zu,\"", i ? "," : "", o->input_index);
    uuid_json(o->uuid);
    printf("\",%u,%u,%d,%d,%zu]", (unsigned)o->properties, (unsigned)o->known_kind,
           (int)o->read_state, (int)o->read_reason, o->read_size);
  }
  printf("],\"diagnostics\":[");
  for (i = 0; i < r->diagnostic_count; ++i) {
    const ftms_cap_diagnostic *d = &out->diagnostics[i];
    printf("%s[%d,%u,", i ? "," : "", (int)d->code, (unsigned)d->known_kind);
    index_json(d->input_index);
    printf("]");
  }
  puts("]}");
}

int main(void) {
  ftms_cap_characteristic chars[MAX_CHARS];
  uint8_t bytes[MAX_CHARS][MAX_BYTES];
  char uuid[33], payload[MAX_BYTES * 2U + 1U], trailing;
  unsigned discovery, scope, count, i, properties, state, reason, bonding, mutable;
  uint32_t generation;
  size_t size;
  ftms_cap_snapshot snapshot;
  ftms_cap_c7_evidence c7;
  ftms_cap_requirements requirements;
  ftms_cap_output out;
  if (scanf("%u %u %" SCNu32 " %u %u %u", &discovery, &scope, &generation, &count, &bonding, &mutable) != 6 ||
       discovery > 3U || scope > 3U || count > MAX_CHARS || bonding > 2U || mutable > 2U) return 64;
  memset(chars, 0, sizeof chars);
  for (i = 0; i < count; ++i) {
    if (scanf("%32s %u %u %u %2048s", uuid, &properties, &state, &reason, payload) != 5 ||
        properties > UINT16_MAX || state > 2U || reason > 5U ||
        !hex(uuid, chars[i].uuid, FTMS_CAP_UUID_BYTES, &size) || size != FTMS_CAP_UUID_BYTES) return 64;
    chars[i].properties = (uint16_t)properties;
    chars[i].read_state = (ftms_cap_read_state)state;
    chars[i].read_reason = (ftms_cap_read_reason)reason;
    if (strcmp(payload, "-") != 0) {
      if (!hex(payload, bytes[i], MAX_BYTES, &size)) return 64;
      chars[i].read_bytes = bytes[i];
      chars[i].read_size = size;
    }
  }
  if (scanf(" %c", &trailing) != EOF) return 64;
  snapshot.discovery = (ftms_cap_discovery)discovery;
  snapshot.service_scope = (ftms_cap_service_scope)scope;
  snapshot.generation = generation;
  snapshot.characteristics = chars;
  snapshot.characteristic_count = count;
  c7.bonding_supported = (ftms_cap_truth)bonding;
  c7.feature_may_change_over_lifetime = (ftms_cap_truth)mutable;
  if (ftms_capability_requirements_with_c7(&snapshot, NULL, &c7, &requirements) != FTMS_OK) return 65;
  memset(&out, 0, sizeof out);
  out.observation_capacity = requirements.observation_count;
  out.diagnostic_capacity = requirements.diagnostic_count;
  out.observations = requirements.observation_count ? calloc(requirements.observation_count, sizeof *out.observations) : NULL;
  out.diagnostics = requirements.diagnostic_count ? calloc(requirements.diagnostic_count, sizeof *out.diagnostics) : NULL;
  if ((requirements.observation_count && !out.observations) || (requirements.diagnostic_count && !out.diagnostics)) {
    free(out.observations); free(out.diagnostics); return 66;
  }
  if (ftms_evaluate_capabilities_with_c7(&snapshot, NULL, &c7, &out) != FTMS_OK) {
    free(out.observations); free(out.diagnostics); return 67;
  }
  report_json(&out);
  free(out.observations);
  free(out.diagnostics);
  return 0;
}
