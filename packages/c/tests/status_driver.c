#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ftms/status.h"

static int parse_number(const char *text, int64_t low, int64_t high,
                        int64_t *out) {
  char *end;
  intmax_t value;

  errno = 0;
  value = strtoimax(text, &end, 10);
  if (errno != 0 || end == text || *end != '\0' ||
      value < (intmax_t)low || value > (intmax_t)high) {
    return 0;
  }
  *out = (int64_t)value;
  return 1;
}

static int hex_digit(char character) {
  if (character >= '0' && character <= '9') return character - '0';
  if (character >= 'a' && character <= 'f') return character - 'a' + 10;
  if (character >= 'A' && character <= 'F') return character - 'A' + 10;
  return -1;
}

static int parse_hex(const char *text, uint8_t *bytes, size_t *size) {
  size_t index;
  size_t length = strlen(text);

  if ((length & 1U) != 0U || length > 2048U) return 0;
  for (index = 0U; index < length / 2U; ++index) {
    int high = hex_digit(text[index * 2U]);
    int low = hex_digit(text[index * 2U + 1U]);
    if (high < 0 || low < 0) return 0;
    bytes[index] = (uint8_t)(high * 16 + low);
  }
  *size = length / 2U;
  return 1;
}

static void print_bytes(const uint8_t *bytes, size_t size) {
  size_t index;

  fputs("{\"bytes\":\"", stdout);
  for (index = 0U; index < size; ++index) printf("%02x", (unsigned)bytes[index]);
  puts("\"}");
}

static size_t operand_count(unsigned opcode) {
  if (opcode == 14U) return 2U;
  if (opcode == 15U) return 3U;
  if (opcode == 16U) return 5U;
  if (opcode == 17U) return 4U;
  if ((opcode >= 2U && opcode <= 6U) || (opcode >= 9U && opcode <= 13U) ||
      opcode == 18U || opcode == 20U) return 1U;
  return 0U;
}

static int operand_bounds(unsigned opcode, size_t index, int64_t *low,
                          int64_t *high) {
  *low = 0;
  *high = 65535;
  if (opcode == 3U || opcode == 4U || opcode == 5U ||
      (opcode == 17U && index < 2U)) {
    *low = -32768;
    *high = 32767;
  } else if (opcode == 6U || (opcode == 17U && index >= 2U)) {
    *high = 255;
  } else if (opcode == 12U) {
    *high = 16777215;
  }
  return operand_count(opcode) != 0U;
}

static int parse_request(ftms_control_request *request, int parameter_tag,
                         char **arguments, size_t argument_count) {
  int64_t values[5] = {0, 0, 0, 0, 0};
  size_t count;
  size_t index;

  if (parameter_tag < 0) return argument_count == 0U;
  count = operand_count((unsigned)parameter_tag);
  if (count == 0U || argument_count != count) return 0;
  for (index = 0U; index < count; ++index) {
    int64_t low;
    int64_t high;
    if (!operand_bounds((unsigned)parameter_tag, index, &low, &high) ||
        !parse_number(arguments[index], low, high, &values[index])) return 0;
  }

  request->opcode = (ftms_control_opcode)parameter_tag;
  switch (parameter_tag) {
    case 2: request->value.speed_centikph = (uint16_t)values[0]; break;
    case 3: request->value.inclination_tenth_percent = (int16_t)values[0]; break;
    case 4: request->value.resistance_tenth_level = (int16_t)values[0]; break;
    case 5: request->value.power_watts = (int16_t)values[0]; break;
    case 6: request->value.heart_rate_bpm = (uint8_t)values[0]; break;
    case 9: request->value.energy_kcal = (uint16_t)values[0]; break;
    case 10: request->value.steps = (uint16_t)values[0]; break;
    case 11: request->value.strides = (uint16_t)values[0]; break;
    case 12: request->value.distance_metres = (uint32_t)values[0]; break;
    case 13: request->value.training_seconds = (uint16_t)values[0]; break;
    case 14: case 15: case 16:
      for (index = 0U; index < count; ++index) {
        request->value.zone_seconds[index] = (uint16_t)values[index];
      }
      break;
    case 17:
      request->value.simulation.wind_millimetres_per_second = (int16_t)values[0];
      request->value.simulation.grade_hundredth_percent = (int16_t)values[1];
      request->value.simulation.crr_ten_thousandth = (uint8_t)values[2];
      request->value.simulation.cw_hundredth_kg_per_m = (uint8_t)values[3];
      break;
    case 18: request->value.wheel_circumference_tenth_mm = (uint16_t)values[0]; break;
    case 20: request->value.cadence_half_rpm = (uint16_t)values[0]; break;
    default: return 0;
  }
  return 1;
}

static void print_request(const ftms_control_request *request) {
  int64_t values[5] = {0, 0, 0, 0, 0};
  size_t count = operand_count((unsigned)request->opcode);
  size_t index;

  switch ((unsigned)request->opcode) {
    case 2: values[0] = request->value.speed_centikph; break;
    case 3: values[0] = request->value.inclination_tenth_percent; break;
    case 4: values[0] = request->value.resistance_tenth_level; break;
    case 5: values[0] = request->value.power_watts; break;
    case 6: values[0] = request->value.heart_rate_bpm; break;
    case 9: values[0] = request->value.energy_kcal; break;
    case 10: values[0] = request->value.steps; break;
    case 11: values[0] = request->value.strides; break;
    case 12: values[0] = request->value.distance_metres; break;
    case 13: values[0] = request->value.training_seconds; break;
    case 14: case 15: case 16:
      for (index = 0U; index < count; ++index) values[index] = request->value.zone_seconds[index];
      break;
    case 17:
      values[0] = request->value.simulation.wind_millimetres_per_second;
      values[1] = request->value.simulation.grade_hundredth_percent;
      values[2] = request->value.simulation.crr_ten_thousandth;
      values[3] = request->value.simulation.cw_hundredth_kg_per_m;
      break;
    case 18: values[0] = request->value.wheel_circumference_tenth_mm; break;
    case 20: values[0] = request->value.cadence_half_rpm; break;
    default: break;
  }
  printf("{\"opcode\":%u,\"operands\":[", (unsigned)request->opcode);
  for (index = 0U; index < count; ++index) {
    printf("%s%" PRId64, index == 0U ? "" : ",", values[index]);
  }
  fputs("]}", stdout);
}

static void print_machine(const ftms_machine_status *status) {
  printf("{\"opcode\":%u,\"action\":%u,\"parameter\":", (unsigned)status->opcode,
         (unsigned)status->action);
  if (status->parameter_present) print_request(&status->parameter);
  else fputs("null", stdout);
  printf(",\"unknownOpcode\":%u,\"reservedValue\":%u,\"truncated\":%u,"
         "\"trailingBytes\":%u}\n", (unsigned)status->unknown_opcode,
         (unsigned)status->reserved_value, (unsigned)status->truncated,
         (unsigned)status->trailing_bytes);
}

static int print_training(const ftms_training_status *status, const uint8_t *input,
                          size_t input_size) {
  size_t index;

  if (status->text_offset > input_size ||
      status->text_size > input_size - status->text_offset) return 0;
  printf("{\"flags\":%u,\"code\":%u,\"textOffset\":%zu,\"textSize\":%zu,"
         "\"textPresent\":%u,\"extendedString\":%u,\"reservedFlags\":%u,"
         "\"reservedValue\":%u,\"invalidFlags\":%u,\"invalidUtf8\":%u,"
         "\"truncated\":%u,\"trailingBytes\":%u,\"textHex\":\"",
         (unsigned)status->flags, (unsigned)status->code, status->text_offset,
         status->text_size, (unsigned)status->text_present,
         (unsigned)status->extended_string, (unsigned)status->reserved_flags,
         (unsigned)status->reserved_value, (unsigned)status->invalid_flags,
         (unsigned)status->invalid_utf8, (unsigned)status->truncated,
         (unsigned)status->trailing_bytes);
  for (index = 0U; index < status->text_size; ++index) {
    printf("%02x", (unsigned)input[status->text_offset + index]);
  }
  puts("\"}");
  return 1;
}

int main(int argc, char **argv) {
  uint8_t bytes[1024];
  uint8_t text[1024];
  size_t size;
  size_t written;
  ftms_result result;

  if (argc < 3) return 64;
  if (strcmp(argv[1], "decode-machine") == 0) {
    ftms_machine_status status;
    if (argc != 3 || !parse_hex(argv[2], bytes, &size)) goto bridge_error;
    result = ftms_decode_machine_status(bytes, size, &status);
    if (result == FTMS_OK) print_machine(&status);
  } else if (strcmp(argv[1], "decode-training") == 0) {
    ftms_training_status status;
    if (argc != 3 || !parse_hex(argv[2], bytes, &size)) goto bridge_error;
    result = ftms_decode_training_status(bytes, size, &status);
    if (result == FTMS_OK && !print_training(&status, bytes, size)) goto bridge_error;
  } else if (strcmp(argv[1], "encode-machine") == 0) {
    ftms_machine_status status = {0};
    int64_t opcode_value;
    int64_t tag_value;
    int64_t action_value;
    uint8_t opcode;
    int parameter_tag;
    uint8_t action;

    if (argc < 5 || !parse_number(argv[2], 0, 255, &opcode_value) ||
        !parse_number(argv[3], -1, 255, &tag_value) ||
        !parse_number(argv[4], 0, 255, &action_value)) goto bridge_error;
    opcode = (uint8_t)opcode_value;
    parameter_tag = (int)tag_value;
    action = (uint8_t)action_value;
    if (!parse_request(&status.parameter, parameter_tag, argv + 5,
                       (size_t)(argc - 5))) goto bridge_error;
    status.opcode = opcode;
    status.action = action;
    status.parameter_present = (uint8_t)(parameter_tag >= 0);
    result = ftms_encode_machine_status(&status, bytes, sizeof bytes, &written);
    if (result == FTMS_OK) print_bytes(bytes, written);
  } else if (strcmp(argv[1], "encode-training") == 0) {
    ftms_training_status status = {0};
    int64_t flags_value;
    int64_t code_value;

    if (argc != 5 || !parse_number(argv[2], 0, 255, &flags_value) ||
        !parse_number(argv[3], 0, 255, &code_value) ||
        !parse_hex(argv[4], text, &size)) goto bridge_error;
    status.flags = (uint8_t)flags_value;
    status.code = (uint8_t)code_value;
    result = ftms_encode_training_status(&status, text, size, bytes, sizeof bytes, &written);
    if (result == FTMS_OK) print_bytes(bytes, written);
  } else {
    return 64;
  }
  if (result != FTMS_OK) printf("{\"error\":%d}\n", (int)result);
  return 0;

bridge_error:
  puts("{\"bridgeError\":true}");
  return 0;
}
