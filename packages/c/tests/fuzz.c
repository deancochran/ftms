#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ftms/capabilities.h"
#include "ftms/control.h"

static uint32_t next(uint32_t *state) {
  *state = *state * UINT32_C(1664525) + UINT32_C(1013904223);
  return *state;
}

static int control_fuzz(uint8_t bytes[16], uint32_t *state) {
  ftms_control_request request, saved_request;
  ftms_control_response response, saved_response;
  uint8_t encoded[16], saved[16];
  size_t size = (size_t)(next(state) % 13U), written = 99U;
  ftms_result result;
  memset(&request, 0xa5, sizeof request); memcpy(&saved_request, &request, sizeof request);
  bytes[0] = (uint8_t)(next(state) % 23U);
  result = ftms_decode_control_request(bytes, size, &request);
  if (result != FTMS_OK) {
    if (memcmp(&request, &saved_request, sizeof request) != 0) return 11;
  } else {
    if (ftms_encode_control_request(&request, encoded, sizeof encoded, &written) != FTMS_OK ||
        written != size || memcmp(bytes, encoded, size) != 0) return 12;
    memcpy(saved, encoded, sizeof saved); written = 99U;
    if (ftms_encode_control_request(&request, encoded, size - 1U, &written) != FTMS_ERROR_LENGTH ||
        written != 99U || memcmp(saved, encoded, sizeof saved) != 0) return 13;
  }
  bytes[0] = 0x80; bytes[1] = (uint8_t)(next(state) % 23U); bytes[2] = (uint8_t)(next(state) % 7U);
  memset(&response, 0xa5, sizeof response); memcpy(&saved_response, &response, sizeof response);
  result = ftms_decode_control_response(bytes, size, &response);
  if (result != FTMS_OK) {
    if (memcmp(&response, &saved_response, sizeof response) != 0) return 14;
  } else if (!response.unknown_result && !response.unknown_request && !response.unexpected_parameters) {
    if (ftms_encode_control_response(&response, encoded, sizeof encoded, &written) != FTMS_OK ||
        written != size || memcmp(bytes, encoded, size) != 0) return 15;
    memcpy(saved, encoded, sizeof saved); written = 99U;
    if (ftms_encode_control_response(&response, encoded, size - 1U, &written) != FTMS_ERROR_LENGTH ||
        written != 99U || memcmp(saved, encoded, sizeof saved) != 0) return 16;
  }
  return 0;
}

static int exercise(uint32_t *state) {
  static const uint8_t sig_uuid[16] = {0,0,0x2a,0xcc,0,0,0x10,0,0x80,0,0,0x80,0x5f,0x9b,0x34,0xfb};
  uint8_t bytes[8][16];
  ftms_cap_characteristic chars[8], saved_chars[8];
  ftms_cap_snapshot snapshot;
  ftms_cap_requirements q;
  ftms_cap_output out;
  struct { uint32_t before; ftms_cap_observation values[8]; uint32_t after; } obs;
  struct { uint32_t before; ftms_cap_diagnostic values[64]; uint32_t after; } diag;
  ftms_cap_observation unused_obs;
  ftms_cap_diagnostic unused_diag;
  size_t i, j, count = (size_t)(next(state) % 9U);
  memset(chars, 0, sizeof chars);
  for (i = 0; i < 8U; ++i) {
    for (j = 0; j < 16U; ++j) bytes[i][j] = (uint8_t)(next(state) >> 24);
    memcpy(chars[i].uuid, sig_uuid, sizeof sig_uuid);
    chars[i].uuid[3] = (uint8_t)(0xccU + next(state) % 16U);
    if (next(state) % 5U == 0U) chars[i].uuid[0] = 1; /* Full UUID recognition. */
    chars[i].properties = (uint16_t)(next(state) >> 16);
    chars[i].read_state = (ftms_cap_read_state)(next(state) % 3U);
    if (chars[i].read_state == FTMS_CAP_READ_SUCCESS) {
      chars[i].read_bytes = bytes[i]; chars[i].read_size = (size_t)(next(state) % 17U);
    } else if (chars[i].read_state == FTMS_CAP_READ_FAILED) {
      chars[i].read_reason = (ftms_cap_read_reason)(next(state) % 6U);
    }
  }
  snapshot.discovery = (ftms_cap_discovery)(next(state) >> 30);
  snapshot.service_scope = (ftms_cap_service_scope)(next(state) >> 30);
  snapshot.generation = next(state);
  snapshot.characteristics = chars; snapshot.characteristic_count = count;
  memcpy(saved_chars, chars, sizeof chars);
  memset(&out, 0, sizeof out);
  memset(&obs, 0xa5, sizeof obs); memset(&diag, 0xa5, sizeof diag);
  memset(&unused_obs, 0xa5, sizeof unused_obs); memset(&unused_diag, 0xa5, sizeof unused_diag);
  if (ftms_capability_requirements(&snapshot, &q) != FTMS_OK ||
      q.observation_count != count || q.diagnostic_count > 64U) return 1;
  out.observations = obs.values; out.observation_capacity = q.observation_count;
  out.diagnostics = diag.values; out.diagnostic_capacity = q.diagnostic_count;
  if (ftms_evaluate_capabilities(&snapshot, &out) != FTMS_OK ||
      out.report.observation_count != count || out.report.diagnostic_count != q.diagnostic_count ||
      out.report.generation != snapshot.generation) return 2;
  if (memcmp(chars, saved_chars, sizeof chars) != 0) return 3;
  if (obs.before != UINT32_C(0xa5a5a5a5) || obs.after != UINT32_C(0xa5a5a5a5) ||
      diag.before != UINT32_C(0xa5a5a5a5) || diag.after != UINT32_C(0xa5a5a5a5)) return 4;
  for (i = count; i < 8U; ++i) {
    if (memcmp(&obs.values[i], &unused_obs, sizeof unused_obs) != 0) return 5;
  }
  for (i = q.diagnostic_count; i < 64U; ++i) {
    if (memcmp(&diag.values[i], &unused_diag, sizeof unused_diag) != 0) return 6;
  }
  for (i = 0; i < count; ++i) {
    if (obs.values[i].input_index != i || memcmp(obs.values[i].uuid, chars[i].uuid, 16) != 0 ||
        obs.values[i].properties != chars[i].properties) return 7;
  }
  /* Capacity errors must leave both output buffers and the report untouched. */
  if (count != 0U || q.diagnostic_count != 0U) {
    ftms_cap_output saved;
    ftms_cap_observation saved_obs[8];
    ftms_cap_diagnostic saved_diag[64];
    if (count != 0U) --out.observation_capacity;
    else --out.diagnostic_capacity;
    memcpy(&saved, &out, sizeof saved);
    memcpy(saved_obs, obs.values, sizeof saved_obs); memcpy(saved_diag, diag.values, sizeof saved_diag);
    if (ftms_evaluate_capabilities(&snapshot, &out) != FTMS_ERROR_LENGTH ||
        memcmp(&saved, &out, sizeof saved) != 0 ||
        memcmp(saved_obs, obs.values, sizeof saved_obs) != 0 ||
        memcmp(saved_diag, diag.values, sizeof saved_diag) != 0) return 8;
  }
  /* Retain the original bounded codec fuzz invariants as well. */
  {
    ftms_features value = {1,2}, saved = value;
    ftms_range range = {FTMS_RANGE_SPEED,1,2,3,4,FTMS_UNIT_WATTS}, before = range;
    size_t size = (size_t)(next(state) % 17U);
    ftms_result result = ftms_decode_features(bytes[0], size, &value);
    if ((result != FTMS_OK && memcmp(&value, &saved, sizeof value) != 0) ||
        (result == FTMS_OK && size != 8U)) return 9;
    result = ftms_decode_range((ftms_range_kind)(next(state) % 7U), bytes[0], size, &range);
    if (result != FTMS_OK && memcmp(&range, &before, sizeof range) != 0) return 10;
  }
  return control_fuzz(bytes[0], state);
}

int main(void) {
  uint32_t state = UINT32_C(1);
  unsigned i;
  for (i = 0; i < 10000U; ++i) {
    int result = exercise(&state);
    if (result != 0) { fprintf(stderr, "fuzz case %u invariant %d\n", i, result); return result; }
  }
  puts("deterministic codec/capability/control fuzz: 10000 inputs passed");
  return 0;
}
