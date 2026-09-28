/* Host-only raw-integer bridge. Invalid bridge input is not a library error. */
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ftms/control.h"

static int number(const char *s, int64_t low, int64_t high, int64_t *out) {
  char *end;
  long long value;
  errno = 0;
  value = strtoll(s, &end, 10);
  if (errno || end == s || *end || value < low || value > high) return 0;
  *out = (int64_t)value;
  return 1;
}
static int digit(char x) {
  if (x >= '0' && x <= '9') return x - '0';
  if (x >= 'a' && x <= 'f') return x - 'a' + 10;
  return -1;
}
static int bytes_in(const char *s, uint8_t *out, size_t *size) {
  size_t i, length = strlen(s);
  if (length % 2U || length > 2048U) return 0;
  for (i = 0; i < length / 2U; ++i) {
    int high = digit(s[i * 2U]), low = digit(s[i * 2U + 1U]);
    if (high < 0 || low < 0) return 0;
    out[i] = (uint8_t)((unsigned)high * 16U + (unsigned)low);
  }
  *size = length / 2U;
  return 1;
}
static void emit_bytes(const uint8_t *bytes, size_t size) {
  size_t i;
  printf("{\"bytes\":\"");
  for (i = 0; i < size; ++i) printf("%02x", (unsigned)bytes[i]);
  puts("\"}");
}
static size_t operand_count(int64_t opcode) {
  switch (opcode) {
    case 0: case 1: case 7: return 0;
    case 14: return 2;
    case 15: return 3;
    case 16: return 5;
    case 17: return 4;
    default: return opcode >= 2 && opcode <= 20 ? 1U : 0U;
  }
}
static int request_in(int argc, char **argv, ftms_control_request *r) {
  int64_t opcode, values[5] = {0};
  size_t i, count;
  if (!number(argv[2], -1, 65535, &opcode)) return 0;
  count = operand_count(opcode);
  if ((size_t)argc != count + 3U) return 0;
  for (i = 0; i < count; ++i) {
    int64_t low = 0, high = UINT16_MAX;
    if (opcode == 3 || opcode == 4 || opcode == 5 || (opcode == 17 && i < 2U)) {
      low = INT16_MIN; high = INT16_MAX;
    } else if (opcode == 6 || (opcode == 17 && i >= 2U)) high = UINT8_MAX;
    else if (opcode == 12) high = UINT32_MAX;
    else if (opcode == 8 || opcode == 19) { low = -1; high = 65535; }
    if (!number(argv[i + 3U], low, high, &values[i])) return 0;
  }
  r->opcode = (ftms_control_opcode)opcode;
  switch (opcode) {
    case 2: r->value.speed_centikph = (uint16_t)values[0]; break;
    case 3: r->value.inclination_tenth_percent = (int16_t)values[0]; break;
    case 4: r->value.resistance_tenth_level = (int16_t)values[0]; break;
    case 5: r->value.power_watts = (int16_t)values[0]; break;
    case 6: r->value.heart_rate_bpm = (uint8_t)values[0]; break;
    case 8: r->value.stop_pause = (ftms_stop_pause_action)values[0]; break;
    case 9: r->value.energy_kcal = (uint16_t)values[0]; break;
    case 10: r->value.steps = (uint16_t)values[0]; break;
    case 11: r->value.strides = (uint16_t)values[0]; break;
    case 12: r->value.distance_metres = (uint32_t)values[0]; break;
    case 13: r->value.training_seconds = (uint16_t)values[0]; break;
    case 14: case 15: case 16:
      for (i = 0; i < count; ++i) r->value.zone_seconds[i] = (uint16_t)values[i];
      break;
    case 17:
      r->value.simulation.wind_millimetres_per_second = (int16_t)values[0];
      r->value.simulation.grade_hundredth_percent = (int16_t)values[1];
      r->value.simulation.crr_ten_thousandth = (uint8_t)values[2];
      r->value.simulation.cw_hundredth_kg_per_m = (uint8_t)values[3];
      break;
    case 18: r->value.wheel_circumference_tenth_mm = (uint16_t)values[0]; break;
    case 19: r->value.spin_down = (ftms_spin_down_action)values[0]; break;
    case 20: r->value.cadence_half_rpm = (uint16_t)values[0]; break;
    default: break;
  }
  return 1;
}
static void request_out(const ftms_control_request *r) {
  int64_t values[5] = {0};
  size_t i, count = operand_count(r->opcode);
  switch (r->opcode) {
    case 2: values[0] = r->value.speed_centikph; break;
    case 3: values[0] = r->value.inclination_tenth_percent; break;
    case 4: values[0] = r->value.resistance_tenth_level; break;
    case 5: values[0] = r->value.power_watts; break;
    case 6: values[0] = r->value.heart_rate_bpm; break;
    case 8: values[0] = r->value.stop_pause; break;
    case 9: values[0] = r->value.energy_kcal; break;
    case 10: values[0] = r->value.steps; break;
    case 11: values[0] = r->value.strides; break;
    case 12: values[0] = r->value.distance_metres; break;
    case 13: values[0] = r->value.training_seconds; break;
    case 14: case 15: case 16:
      for (i = 0; i < count; ++i) values[i] = r->value.zone_seconds[i];
      break;
    case 17:
      values[0] = r->value.simulation.wind_millimetres_per_second;
      values[1] = r->value.simulation.grade_hundredth_percent;
      values[2] = r->value.simulation.crr_ten_thousandth;
      values[3] = r->value.simulation.cw_hundredth_kg_per_m;
      break;
    case 18: values[0] = r->value.wheel_circumference_tenth_mm; break;
    case 19: values[0] = r->value.spin_down; break;
    case 20: values[0] = r->value.cadence_half_rpm; break;
    default: break;
  }
  printf("{\"opcode\":%u,\"operands\":[", (unsigned)r->opcode);
  for (i = 0; i < count; ++i) printf("%s%" PRId64, i ? "," : "", values[i]);
  puts("]}");
}
static void response_out(const ftms_control_response *r) {
  printf("{\"requestOpcode\":%u,\"resultCode\":%u,\"parameter\":%u,\"low\":%u,\"high\":%u,"
         "\"unknownRequest\":%u,\"unknownResult\":%u,\"unexpectedParameters\":%u}\n",
         (unsigned)r->request_opcode, (unsigned)r->result_code, (unsigned)r->parameter,
         (unsigned)r->spin_down_low_centikph, (unsigned)r->spin_down_high_centikph,
         (unsigned)r->unknown_request, (unsigned)r->unknown_result, (unsigned)r->unexpected_parameters);
}
int main(int argc, char **argv) {
  uint8_t bytes[1024];
  size_t size, written;
  ftms_result result;
  if (argc < 3) return 64;
  if (!strcmp(argv[1], "decode-request") || !strcmp(argv[1], "decode-response")) {
    if (argc != 3 || !bytes_in(argv[2], bytes, &size)) { puts("{\"bridgeError\":true}"); return 0; }
    if (!strcmp(argv[1], "decode-request")) {
      ftms_control_request request;
      result = ftms_decode_control_request(bytes, size, &request);
      if (result == FTMS_OK) request_out(&request);
    } else {
      ftms_control_response response;
      result = ftms_decode_control_response(bytes, size, &response);
      if (result == FTMS_OK) response_out(&response);
    }
  } else if (!strcmp(argv[1], "encode-request")) {
    ftms_control_request request = {0};
    if (!request_in(argc, argv, &request)) { puts("{\"bridgeError\":true}"); return 0; }
    result = ftms_encode_control_request(&request, bytes, sizeof bytes, &written);
    if (result == FTMS_OK) emit_bytes(bytes, written);
  } else if (!strcmp(argv[1], "encode-response")) {
    ftms_control_response response = {0};
    int64_t values[5];
    size_t i;
    if (argc != 7) return 64;
    for (i = 0; i < 5U; ++i) {
      if (!number(argv[i + 2U], i == 2U ? -1 : 0, i < 2U ? UINT8_MAX : UINT16_MAX, &values[i])) {
        puts("{\"bridgeError\":true}"); return 0;
      }
    }
    response.request_opcode = (uint8_t)values[0]; response.result_code = (uint8_t)values[1];
    response.parameter = (ftms_control_response_parameter)values[2];
    response.spin_down_low_centikph = (uint16_t)values[3]; response.spin_down_high_centikph = (uint16_t)values[4];
    result = ftms_encode_control_response(&response, bytes, sizeof bytes, &written);
    if (result == FTMS_OK) emit_bytes(bytes, written);
  } else return 64;
  if (result != FTMS_OK) printf("{\"error\":%d}\n", (int)result);
  return 0;
}
